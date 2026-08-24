from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models import (Paciente, TipoIdentificacion, TipoUsuarioPaciente,
                        Sexo, Pais, Departamento, Municipio)
from app.pacientes import pacientes_bp


@pacientes_bp.route('/')
@login_required
def lista():
    q = request.args.get('q', '').strip()
    query = Paciente.query
    if q:
        query = query.filter(
            db.or_(
                Paciente.identificacion.ilike(f'%{q}%'),
                Paciente.nombres.ilike(f'%{q}%'),
                Paciente.apellidos.ilike(f'%{q}%')
            )
        )
    pacientes = query.order_by(Paciente.apellidos, Paciente.nombres).limit(200).all()
    return render_template('pacientes/lista.html', pacientes=pacientes, q=q)


@pacientes_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    return _form_paciente(None)


@pacientes_bp.route('/<identificacion>/editar', methods=['GET', 'POST'])
@login_required
def editar(identificacion):
    p = Paciente.query.get_or_404(identificacion)
    return _form_paciente(p)


@pacientes_bp.route('/buscar')
@login_required
def buscar():
    """Búsqueda rápida para autocompletado (AJAX)"""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    pacientes = Paciente.query.filter(
        db.or_(
            Paciente.identificacion.ilike(f'%{q}%'),
            Paciente.nombres.ilike(f'%{q}%'),
            Paciente.apellidos.ilike(f'%{q}%')
        )
    ).filter_by(estado=True).limit(10).all()
    return jsonify([{
        'identificacion': p.identificacion,
        'nombre_completo': p.nombre_completo,
        'tipo_id': p.tipo_id.codigo if p.tipo_id else '',
    } for p in pacientes])


@pacientes_bp.route('/<identificacion>/detalle')
@login_required
def detalle(identificacion):
    p = Paciente.query.get_or_404(identificacion)
    return render_template('pacientes/detalle.html', paciente=p)


@pacientes_bp.route('/<identificacion>/toggle')
@login_required
def toggle(identificacion):
    p = Paciente.query.get_or_404(identificacion)
    p.estado = not p.estado
    db.session.commit()
    estado = 'activado' if p.estado else 'desactivado'
    flash(f'Paciente {estado}.', 'success')
    return redirect(url_for('pacientes.lista'))


def _form_paciente(paciente):
    tipos_id = TipoIdentificacion.query.filter_by(estado=True).order_by(TipoIdentificacion.nombre).all()
    tipos_usuario = TipoUsuarioPaciente.query.filter_by(estado=True).order_by(TipoUsuarioPaciente.nombre).all()
    sexos = Sexo.query.order_by(Sexo.nombre).all()
    paises = Pais.query.filter_by(estado=True).order_by(Pais.nombre).all()

    if request.method == 'POST':
        identificacion = request.form.get('identificacion', '').strip()
        nombres = request.form.get('nombres', '').strip()
        apellidos = request.form.get('apellidos', '').strip()
        fecha_nac = request.form.get('fecha_nacimiento', '')
        tipo_id_id = request.form.get('tipo_id_id')
        sexo_id = request.form.get('sexo_id')
        tipo_usuario_id = request.form.get('tipo_usuario_id') or None
        pais_nac_id = request.form.get('pais_nacimiento_id') or None
        pais_res_id = request.form.get('pais_residencia_id') or None
        departamento_id = request.form.get('departamento_id') or None
        municipio_id = request.form.get('municipio_id') or None
        direccion = request.form.get('direccion', '').strip()
        telefono = request.form.get('telefono', '').strip()
        celular = request.form.get('celular', '').strip()
        email = request.form.get('email', '').strip()
        estado = request.form.get('estado') == 'on'

        if not identificacion or not nombres or not apellidos or not fecha_nac:
            flash('Identificación, nombres, apellidos y fecha de nacimiento son obligatorios.', 'danger')
        else:
            try:
                fecha_nac_dt = datetime.strptime(fecha_nac, '%Y-%m-%d').date()
            except ValueError:
                flash('Formato de fecha incorrecto.', 'danger')
                return _render_form(paciente, tipos_id, tipos_usuario, sexos, paises)

            tipo_id = TipoIdentificacion.query.get(tipo_id_id) if tipo_id_id else None
            if tipo_id and tipo_id.codigo in {'CE', 'PA'} and pais_nac_id and pais_res_id and pais_nac_id == pais_res_id:
                flash('Para tipo de documento CE o PA, el país de nacimiento debe ser diferente al país de residencia.', 'danger')
                return _render_form(paciente, tipos_id, tipos_usuario, sexos, paises)

            if paciente is None:
                if Paciente.query.get(identificacion):
                    flash(f'Ya existe un paciente con identificación {identificacion}.', 'danger')
                    return _render_form(paciente, tipos_id, tipos_usuario, sexos, paises)
                p = Paciente(
                    identificacion=identificacion,
                    nombres=nombres, apellidos=apellidos,
                    fecha_nacimiento=fecha_nac_dt,
                    tipo_id_id=tipo_id_id, sexo_id=sexo_id,
                    tipo_usuario_id=tipo_usuario_id,
                    pais_nacimiento_id=pais_nac_id, pais_residencia_id=pais_res_id,
                    departamento_id=departamento_id, municipio_id=municipio_id,
                    direccion=direccion, telefono=telefono, celular=celular,
                    email=email, estado=estado,
                    usuario_crea_id=current_user.id
                )
                db.session.add(p)
                flash('Paciente registrado correctamente.', 'success')
            else:
                paciente.nombres = nombres
                paciente.apellidos = apellidos
                paciente.fecha_nacimiento = fecha_nac_dt
                paciente.tipo_id_id = tipo_id_id
                paciente.sexo_id = sexo_id
                paciente.tipo_usuario_id = tipo_usuario_id
                paciente.pais_nacimiento_id = pais_nac_id
                paciente.pais_residencia_id = pais_res_id
                paciente.departamento_id = departamento_id
                paciente.municipio_id = municipio_id
                paciente.direccion = direccion
                paciente.telefono = telefono
                paciente.celular = celular
                paciente.email = email
                paciente.estado = estado
                flash('Paciente actualizado correctamente.', 'success')

            db.session.commit()
            return redirect(url_for('pacientes.lista'))

    return _render_form(paciente, tipos_id, tipos_usuario, sexos, paises)


def _render_form(paciente, tipos_id, tipos_usuario, sexos, paises):
    if request.method == 'POST':
        selected_tipo_id = request.form.get('tipo_id_id', '')
        selected_tipo_usuario = request.form.get('tipo_usuario_id', '')
        selected_sexo = request.form.get('sexo_id', '')
        selected_pais_nacimiento = request.form.get('pais_nacimiento_id', '')
        selected_pais_residencia = request.form.get('pais_residencia_id', '')
        selected_departamento = request.form.get('departamento_id', '')
        selected_municipio = request.form.get('municipio_id', '')
    else:
        selected_tipo_id = str(paciente.tipo_id_id) if paciente and paciente.tipo_id_id else ''
        selected_tipo_usuario = str(paciente.tipo_usuario_id) if paciente and paciente.tipo_usuario_id else ''
        selected_sexo = str(paciente.sexo_id) if paciente and paciente.sexo_id else ''
        selected_pais_nacimiento = str(paciente.pais_nacimiento_id) if paciente and paciente.pais_nacimiento_id else ''
        selected_pais_residencia = str(paciente.pais_residencia_id) if paciente and paciente.pais_residencia_id else ''
        selected_departamento = str(paciente.departamento_id) if paciente and paciente.departamento_id else ''
        selected_municipio = str(paciente.municipio_id) if paciente and paciente.municipio_id else ''

        # Por defecto Colombia al crear un paciente nuevo
        if not paciente:
            colombia = Pais.query.filter_by(codigo='170').first()
            if colombia:
                selected_pais_nacimiento = str(colombia.id)
                selected_pais_residencia = str(colombia.id)

    departamentos = []
    municipios = []
    if selected_pais_residencia:
        departamentos = Departamento.query.filter_by(
            pais_id=selected_pais_residencia, estado=True).order_by(Departamento.nombre).all()
    if selected_departamento:
        municipios = Municipio.query.filter_by(
            departamento_id=selected_departamento, estado=True).order_by(Municipio.nombre).all()

    return render_template('pacientes/form.html',
                           paciente=paciente,
                           tipos_id=tipos_id,
                           tipos_usuario=tipos_usuario,
                           sexos=sexos,
                           paises=paises,
                           departamentos=departamentos,
                           municipios=municipios,
                           selected_tipo_id=selected_tipo_id,
                           selected_tipo_usuario=selected_tipo_usuario,
                           selected_sexo=selected_sexo,
                           selected_pais_nacimiento=selected_pais_nacimiento,
                           selected_pais_residencia=selected_pais_residencia,
                           selected_departamento=selected_departamento,
                           selected_municipio=selected_municipio)
