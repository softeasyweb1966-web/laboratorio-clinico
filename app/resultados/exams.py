from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify,
)
from flask_login import login_required, current_user
from app.models import Exam, Parameter, ReferenceValue
from app import db

exams_bp = Blueprint('exams', __name__)


# ---------------------------------------------------------------------------
# Exam list
# ---------------------------------------------------------------------------

@exams_bp.route('/')
@login_required
def list_exams():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    query = Exam.query
    if q:
        query = query.filter(
            Exam.name.ilike(f'%{q}%') | Exam.code.ilike(f'%{q}%')
        )
    if category:
        query = query.filter_by(category=category)
    exams = query.order_by(Exam.name).all()
    return render_template('exams/list.html', exams=exams, q=q, category=category)


# ---------------------------------------------------------------------------
# Create / edit exam
# ---------------------------------------------------------------------------

@exams_bp.route('/new', methods=['GET', 'POST'])
@login_required
def exam_new():
    if request.method == 'POST':
        exam = _exam_from_form(Exam())
        db.session.add(exam)
        db.session.commit()
        flash('Examen creado correctamente.', 'success')
        return redirect(url_for('exams.exam_detail', exam_id=exam.id))
    return render_template('exams/form.html', exam=None)


@exams_bp.route('/<int:exam_id>/edit', methods=['GET', 'POST'])
@login_required
def exam_edit(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if request.method == 'POST':
        _exam_from_form(exam)
        db.session.commit()
        flash('Examen actualizado.', 'success')
        return redirect(url_for('exams.exam_detail', exam_id=exam.id))
    return render_template('exams/form.html', exam=exam)


@exams_bp.route('/<int:exam_id>')
@login_required
def exam_detail(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    params = exam.parameters.order_by(Parameter.order_index).all()
    return render_template('exams/detail.html', exam=exam, params=params)


@exams_bp.route('/<int:exam_id>/delete', methods=['POST'])
@login_required
def exam_delete(exam_id):
    if current_user.role != 'admin':
        flash('Acceso restringido.', 'danger')
        return redirect(url_for('exams.list_exams'))
    exam = Exam.query.get_or_404(exam_id)
    exam.active = False
    db.session.commit()
    flash('Examen desactivado.', 'warning')
    return redirect(url_for('exams.list_exams'))


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

@exams_bp.route('/<int:exam_id>/parameters/new', methods=['GET', 'POST'])
@login_required
def parameter_new(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if request.method == 'POST':
        param = _param_from_form(Parameter(exam_id=exam_id))
        db.session.add(param)
        db.session.commit()
        _save_reference_values(param, request.form)
        flash('Parámetro agregado.', 'success')
        return redirect(url_for('exams.exam_detail', exam_id=exam_id))
    return render_template('exams/parameter_form.html', exam=exam, param=None)


@exams_bp.route('/<int:exam_id>/parameters/<int:param_id>/edit', methods=['GET', 'POST'])
@login_required
def parameter_edit(exam_id, param_id):
    exam = Exam.query.get_or_404(exam_id)
    param = Parameter.query.get_or_404(param_id)
    if request.method == 'POST':
        _param_from_form(param)
        db.session.commit()
        # Remove old reference values and re-add
        ReferenceValue.query.filter_by(parameter_id=param.id).delete()
        db.session.flush()
        _save_reference_values(param, request.form)
        flash('Parámetro actualizado.', 'success')
        return redirect(url_for('exams.exam_detail', exam_id=exam_id))
    ref_values = param.reference_values.all()
    return render_template('exams/parameter_form.html', exam=exam, param=param, ref_values=ref_values)


@exams_bp.route('/<int:exam_id>/parameters/<int:param_id>/delete', methods=['POST'])
@login_required
def parameter_delete(exam_id, param_id):
    param = Parameter.query.get_or_404(param_id)
    param.active = False
    db.session.commit()
    flash('Parámetro desactivado.', 'warning')
    return redirect(url_for('exams.exam_detail', exam_id=exam_id))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exam_from_form(exam):
    exam.code = request.form.get('code', '').strip().upper()
    exam.integration_code = request.form.get('integration_code', '').strip().upper() or None
    exam.name = request.form.get('name', '').strip()
    exam.category = request.form.get('category', 'human')
    exam.description = request.form.get('description', '').strip()
    exam.technique = request.form.get('technique', '').strip()
    exam.equipment = request.form.get('equipment', '').strip()
    exam.method = request.form.get('method', '').strip()
    exam.sample_type = request.form.get('sample_type', '').strip()
    return exam


def _param_from_form(param):
    param.name = request.form.get('name', '').strip()
    param.result_type = request.form.get('result_type', 'decimal')
    param.default_units = request.form.get('default_units', '').strip()
    param.is_fixed = bool(request.form.get('is_fixed'))
    param.fixed_value = request.form.get('fixed_value', '').strip()
    param.order_index = int(request.form.get('order_index', 0) or 0)
    param.notes = request.form.get('notes', '').strip()
    return param


def _save_reference_values(param, form):
    genders = form.getlist('rv_gender[]')
    min_ages = form.getlist('rv_min_age[]')
    max_ages = form.getlist('rv_max_age[]')
    ref_types = form.getlist('rv_ref_type[]')
    min_vals = form.getlist('rv_min_value[]')
    max_vals = form.getlist('rv_max_value[]')
    exact_vals = form.getlist('rv_exact_value[]')
    text_vals = form.getlist('rv_text_value[]')
    units_list = form.getlist('rv_units[]')

    # Rellenar listas cortas con cadenas vacias para igualar longitud
    n = len(ref_types)
    def _pad(lst): return lst + [''] * (n - len(lst))
    min_vals   = _pad(min_vals)
    max_vals   = _pad(max_vals)
    exact_vals = _pad(exact_vals)
    text_vals  = _pad(text_vals)

    for i in range(n):
        rv = ReferenceValue(parameter_id=param.id)
        rv.gender = genders[i] if i < len(genders) else None
        rv.min_age = _int_or_none(min_ages[i] if i < len(min_ages) else '')
        rv.max_age = _int_or_none(max_ages[i] if i < len(max_ages) else '')
        rv.ref_type = ref_types[i]
        rv.min_value = _float_or_none(min_vals[i])
        rv.max_value = _float_or_none(max_vals[i])
        rv.exact_value = _float_or_none(exact_vals[i])
        rv.text_value = text_vals[i]
        rv.units = units_list[i] if i < len(units_list) else ''
        db.session.add(rv)
    db.session.commit()


def _int_or_none(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _float_or_none(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
