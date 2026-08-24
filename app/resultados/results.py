import io
import os

from flask import (
    Blueprint, current_app, flash, redirect, render_template, request, send_file,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.models import (
    Exam, LayoutCell, Order, OrderExam, Parameter, ParameterResult, Patient,
    Result, User, UserResultProfile,
)
from app.services.pdf_generator import generate_result_pdf
from app.services.reference_checker import check_parameter_value

results_bp = Blueprint('results', __name__)


def _requested_exams_for_order(order):
    details = order.requested_exams.order_by(OrderExam.sequence).all()
    if not details:
        return [], []

    available_exams = Exam.query.filter_by(active=True).order_by(Exam.name).all()
    exam_index = {}
    for exam in available_exams:
        keys = {exam.code.upper()}
        if exam.integration_code:
            keys.add(exam.integration_code.upper())
        for key in keys:
            exam_index.setdefault(key, []).append(exam)

    resolved = []
    missing_codes = []
    seen_exam_ids = set()

    for detail in details:
        normalized_code = (detail.requested_code or '').strip().upper()
        matched = False
        for exam in exam_index.get(normalized_code, []):
            matched = True
            if exam.id not in seen_exam_ids:
                resolved.append(exam)
                seen_exam_ids.add(exam.id)
        if not matched and normalized_code not in missing_codes:
            missing_codes.append(normalized_code)

    return resolved, missing_codes


def _order_contains_exam(order, exam):
    return any(exam.matches_requested_code(item.requested_code) for item in order.requested_exams)


def _eligible_users(*roles):
    role_filters = [User.rol == 'admin']
    if roles:
        role_filters.append(User.results_profile.has(UserResultProfile.role.in_(roles)))

    return (
        User.query
        .filter(User.activo.is_(True))
        .filter(db.or_(*role_filters))
        .order_by(User.nombre)
        .all()
    )


@results_bp.route('/')
@login_required
def search():
    consecutive = request.args.get('consecutive', '').strip()
    exam_code = request.args.get('exam_code', '').strip().upper()
    order = None
    selected_exam = None
    exams = []
    missing_codes = []

    if consecutive:
        order = Order.query.filter_by(consecutive=consecutive).first()
        if not order:
            flash('No se encontrÃ³ la atenciÃ³n con ese consecutivo.', 'warning')

    if order:
        exams, missing_codes = _requested_exams_for_order(order)
        if exam_code:
            selected_exam = next(
                (exam for exam in exams if exam.matches_requested_code(exam_code)),
                None,
            )
            if not selected_exam:
                flash('El examen no fue solicitado en esta atenciÃ³n.', 'warning')

    if order and selected_exam:
        return redirect(url_for('results.register', order_id=order.id, exam_id=selected_exam.id))

    return render_template(
        'results/search.html',
        order=order,
        exams=exams,
        missing_codes=missing_codes,
        consecutive=consecutive,
        exam_code=exam_code,
    )


@results_bp.route('/register/<order_id>/<int:exam_id>', methods=['GET', 'POST'])
@login_required
def register(order_id, exam_id):
    order = Order.query.get_or_404(order_id)
    exam = Exam.query.get_or_404(exam_id)
    if not _order_contains_exam(order, exam):
        flash('El examen seleccionado no fue solicitado en esta atenciÃ³n.', 'danger')
        return redirect(url_for('results.search', consecutive=order.consecutive))

    patient = order.patient
    params = exam.parameters.filter_by(active=True).order_by(Parameter.order_index).all()
    cells = exam.layout_cells.filter(LayoutCell.row >= 0).order_by(LayoutCell.row, LayoutCell.col).all()

    prev_results = (
        Result.query
        .join(Order)
        .filter(
            Order.patient_id == patient.document,
            Result.exam_id == exam_id,
            Result.status.in_(['final', 'approved']),
        )
        .order_by(Result.date.desc())
        .limit(5)
        .all()
    )

    bacteriologists = _eligible_users('bacteriologist')
    reviewers = _eligible_users('reviewer')
    existing = Result.query.filter_by(order_id=order_id, exam_id=exam_id, status='draft').first()

    if request.method == 'POST':
        action = request.form.get('action', 'save')

        if action == 'approve' and current_user.role not in ('reviewer', 'admin'):
            flash('Solo un revisor o administrador puede aprobar resultados.', 'danger')
            return redirect(url_for('results.register', order_id=order_id, exam_id=exam_id))

        bacteriologist_id = request.form.get('bacteriologist_id', type=int)
        bacteriologist = db.session.get(User, bacteriologist_id) if bacteriologist_id else None
        signature_path = (
            os.path.join(current_app.config['UPLOAD_FOLDER'], bacteriologist.signature_image)
            if bacteriologist and bacteriologist.signature_image else None
        )
        if not bacteriologist or not signature_path or not os.path.isfile(signature_path):
            flash(
                'El bacteriÃ³logo seleccionado debe tener una firma cargada antes de registrar el resultado.',
                'danger',
            )
            return redirect(url_for('results.register', order_id=order_id, exam_id=exam_id))

        result = existing or Result(order_id=order_id, exam_id=exam_id)
        if not existing:
            result.generate_qr_token()
            db.session.add(result)
            db.session.flush()

        result.bacteriologist_id = bacteriologist.id
        reviewer_id = request.form.get('reviewer_id', type=int)
        result.reviewer_id = reviewer_id or None
        result.notes = request.form.get('notes', '').strip()
        result.status = {
            'save': 'draft',
            'finalize': 'final',
            'approve': 'approved',
        }.get(action, 'draft')

        ParameterResult.query.filter_by(result_id=result.id).delete()
        db.session.flush()

        alarms = []
        for param in params:
            if param.is_fixed:
                continue
            value = request.form.get(f'param_{param.id}', '').strip()
            units = request.form.get(f'units_{param.id}', param.default_units or '').strip()
            out_of_range, alarm_desc = check_parameter_value(param, value, patient.age, patient.gender)
            flagged = bool(request.form.get(f'flag_{param.id}'))
            db.session.add(
                ParameterResult(
                    result_id=result.id,
                    parameter_id=param.id,
                    value=value,
                    units=units,
                    out_of_range=out_of_range,
                    flagged=flagged or out_of_range,
                )
            )
            if out_of_range:
                alarms.append({'param': param.name, 'desc': alarm_desc, 'value': value})

        db.session.commit()

        if alarms and action == 'save':
            alarm_msgs = '; '.join(f"{item['param']}: {item['value']} (ref: {item['desc']})" for item in alarms)
            flash(f'Valores fuera de rango: {alarm_msgs}', 'warning')

        if action in ('finalize', 'approve'):
            flash('Resultado guardado exitosamente.', 'success')
            return redirect(url_for('results.result_detail', result_id=result.id))

        flash('Borrador guardado.', 'info')
        return redirect(url_for('results.register', order_id=order_id, exam_id=exam_id))

    grid = _cells_to_grid(cells)
    existing_values = {}
    existing_units = {}
    if existing:
        for parameter_result in existing.parameter_results.all():
            existing_values[parameter_result.parameter_id] = parameter_result.value
            existing_units[parameter_result.parameter_id] = parameter_result.units

    return render_template(
        'results/form.html',
        order=order,
        exam=exam,
        patient=patient,
        params=params,
        grid=grid,
        prev_results=prev_results,
        bacteriologists=bacteriologists,
        reviewers=reviewers,
        existing=existing,
        existing_values=existing_values,
        existing_units=existing_units,
    )


@results_bp.route('/<int:result_id>')
@login_required
def result_detail(result_id):
    result = Result.query.get_or_404(result_id)
    order = result.order
    exam = result.exam
    cells = exam.layout_cells.filter(LayoutCell.row >= 0).order_by(LayoutCell.row, LayoutCell.col).all()
    grid = _cells_to_grid(cells)
    pr_map = {pr.parameter_id: pr for pr in result.parameter_results.all()}
    return render_template(
        'results/detail.html',
        result=result,
        order=order,
        exam=exam,
        grid=grid,
        pr_map=pr_map,
    )


@results_bp.route('/<int:result_id>/pdf')
@login_required
def result_pdf(result_id):
    result = Result.query.get_or_404(result_id)
    pdf_bytes = generate_result_pdf(result)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f'resultado_{result.id}.pdf',
    )


@results_bp.route('/verify/<token>')
def verify(token):
    result = Result.query.filter_by(qr_token=token).first_or_404()
    return render_template('results/verify.html', result=result)


@results_bp.route('/list')
@login_required
def list_results():
    q = request.args.get('q', '').strip()
    query = Result.query.join(Order).join(Patient, Order.patient_id == Patient.document)
    if q:
        search_term = f'%{q}%'
        query = query.filter(
            db.or_(
                Order.consecutive.ilike(search_term),
                Patient.document.ilike(search_term),
                Patient.nombres.ilike(search_term),
                Patient.apellidos.ilike(search_term),
            )
        )
    results = query.order_by(Result.date.desc()).limit(100).all()
    return render_template('results/list.html', results=results, q=q)


def _cells_to_grid(cells):
    if not cells:
        return []

    max_row = max(cell.row + cell.rowspan - 1 for cell in cells)
    max_col = max(cell.col + cell.colspan - 1 for cell in cells)

    covered = set()
    grid_map = {}
    for cell in sorted(cells, key=lambda item: (item.row, item.col)):
        grid_map[(cell.row, cell.col)] = cell
        for row in range(cell.row, cell.row + cell.rowspan):
            for col in range(cell.col, cell.col + cell.colspan):
                covered.add((row, col))

    rows = []
    for row in range(max_row + 1):
        rendered_row = []
        for col in range(max_col + 1):
            if (row, col) in grid_map:
                rendered_row.append(grid_map[(row, col)])
            elif (row, col) not in covered:
                rendered_row.append(None)
        rows.append(rendered_row)
    return rows
