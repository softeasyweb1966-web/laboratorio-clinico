from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from app.main import main_bp
from app.models import AtencionEncabezado, Paciente, Cliente
from app import db
from datetime import date


@main_bp.route('/')
@login_required
def index():
    hoy = date.today()
    atenciones_hoy = AtencionEncabezado.query.filter(
        db.func.date(AtencionEncabezado.fecha_hora_ingreso) == hoy
    ).count()
    total_pacientes = Paciente.query.filter_by(estado=True).count()
    total_clientes = Cliente.query.filter_by(estado=True).count()
    atenciones_pendientes = AtencionEncabezado.query.filter_by(estado='Ingresado').count()

    stats = {
        'atenciones_hoy': atenciones_hoy,
        'total_pacientes': total_pacientes,
        'total_clientes': total_clientes,
        'atenciones_pendientes': atenciones_pendientes,
    }
    return render_template('main/index.html', stats=stats)
