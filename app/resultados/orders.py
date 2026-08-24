from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app import db
from app.models import Exam, Order, OrderExam, Patient

orders_bp = Blueprint('orders', __name__)


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


@orders_bp.route('/')
@login_required
def list_orders():
    q = request.args.get('q', '').strip()
    query = Order.query.join(Patient, Order.patient_id == Patient.document)
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
    orders = query.order_by(Order.fecha_hora_ingreso.desc()).limit(100).all()
    return render_template('orders/list.html', orders=orders, q=q)


@orders_bp.route('/new', methods=['GET', 'POST'])
@login_required
def order_new():
    flash('Las atenciones ahora se crean en el aplicativo principal de laboratorio.', 'info')
    return redirect(url_for('orders.list_orders'))


@orders_bp.route('/<order_id>/edit', methods=['GET', 'POST'])
@login_required
def order_edit(order_id):
    flash('La ediciÃ³n de atenciones debe hacerse en el aplicativo principal de laboratorio.', 'info')
    return redirect(url_for('orders.order_detail', order_id=order_id))


@orders_bp.route('/<order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    requested_exams, missing_codes = _requested_exams_for_order(order)
    return render_template(
        'orders/detail.html',
        order=order,
        requested_exams=requested_exams,
        missing_codes=missing_codes,
    )


@orders_bp.route('/patients')
@login_required
def patients_list():
    q = request.args.get('q', '').strip()
    query = Patient.query.filter_by(estado=True)
    if q:
        search_term = f'%{q}%'
        query = query.filter(
            db.or_(
                Patient.document.ilike(search_term),
                Patient.nombres.ilike(search_term),
                Patient.apellidos.ilike(search_term),
            )
        )
    patients = query.order_by(Patient.apellidos, Patient.nombres).limit(100).all()
    return render_template('orders/patients.html', patients=patients, q=q)


@orders_bp.route('/patients/new', methods=['GET', 'POST'])
@login_required
def patient_new():
    flash('Los pacientes se administran en el aplicativo principal de laboratorio.', 'info')
    return redirect(url_for('orders.patients_list'))


@orders_bp.route('/patients/<patient_id>/edit', methods=['GET', 'POST'])
@login_required
def patient_edit(patient_id):
    flash('La ediciÃ³n de pacientes debe hacerse en el aplicativo principal de laboratorio.', 'info')
    return redirect(url_for('orders.patients_list'))
