from flask import Blueprint, jsonify, request
from flask_login import login_required

from app import db
from app.models import Exam, Order, OrderExam, Parameter, Patient, Result

api_bp = Blueprint('api', __name__)


@api_bp.route('/exams/search')
@login_required
def exam_search():
    q = request.args.get('q', '').strip()
    search_term = f'%{q}%'
    exams = (
        Exam.query
        .filter(
            Exam.active.is_(True),
            db.or_(
                Exam.name.ilike(search_term),
                Exam.code.ilike(search_term),
                Exam.integration_code.ilike(search_term),
            ),
        )
        .order_by(Exam.name)
        .limit(20)
        .all()
    )
    return jsonify([
        {
            'id': exam.id,
            'code': exam.code,
            'integration_code': exam.integration_code,
            'name': exam.name,
        }
        for exam in exams
    ])


@api_bp.route('/patients/search')
@login_required
def patient_search():
    q = request.args.get('q', '').strip()
    search_term = f'%{q}%'
    patients = (
        Patient.query
        .filter(
            Patient.estado.is_(True),
            db.or_(
                Patient.document.ilike(search_term),
                Patient.nombres.ilike(search_term),
                Patient.apellidos.ilike(search_term),
            ),
        )
        .order_by(Patient.apellidos, Patient.nombres)
        .limit(20)
        .all()
    )
    return jsonify([
        {
            'id': patient.id,
            'document': patient.document,
            'name': patient.name,
            'gender': patient.gender,
            'age': patient.age,
        }
        for patient in patients
    ])


@api_bp.route('/orders/search')
@login_required
def order_search():
    q = request.args.get('q', '').strip()
    search_term = f'%{q}%'
    orders = (
        Order.query
        .join(Patient, Order.patient_id == Patient.document)
        .filter(
            db.or_(
                Order.consecutive.ilike(search_term),
                Patient.document.ilike(search_term),
                Patient.nombres.ilike(search_term),
                Patient.apellidos.ilike(search_term),
            )
        )
        .order_by(Order.fecha_hora_ingreso.desc())
        .limit(20)
        .all()
    )
    return jsonify([
        {
            'id': order.id,
            'consecutive': order.consecutive,
            'patient_name': order.patient.name,
            'patient_document': order.patient.document,
            'date': order.date.strftime('%Y-%m-%d'),
            'requested_codes': [detail.requested_code for detail in order.requested_exams.order_by(OrderExam.sequence)],
        }
        for order in orders
    ])


@api_bp.route('/results/<int:result_id>/parameter-values')
@login_required
def parameter_values(result_id):
    result = Result.query.get_or_404(result_id)
    values = []
    for parameter_result in result.parameter_results.all():
        values.append(
            {
                'parameter_id': parameter_result.parameter_id,
                'parameter_name': parameter_result.parameter.name,
                'value': parameter_result.value,
                'units': parameter_result.units,
                'out_of_range': parameter_result.out_of_range,
                'flagged': parameter_result.flagged,
            }
        )
    return jsonify({'date': result.date.strftime('%Y-%m-%d'), 'values': values})


@api_bp.route('/parameters/<int:param_id>/units-suggestions')
@login_required
def units_suggestions(param_id):
    parameter = Parameter.query.get_or_404(param_id)
    units = set()
    if parameter.default_units:
        units.add(parameter.default_units)
    for reference_value in parameter.reference_values:
        if reference_value.units:
            units.add(reference_value.units)
    return jsonify(sorted(units))
