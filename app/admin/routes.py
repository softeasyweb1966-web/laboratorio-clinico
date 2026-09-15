import os
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import (Usuario, Modulo, Pais, Departamento, Municipio,
                        TipoIdentificacion, TipoUsuarioPaciente, Sexo,
                        FormaPago, NumeracionInicial, ConfigRips, PersonaAtiende,
                        UserResultProfile)
from app.admin import admin_bp
from functools import wraps

ALLOWED_IMG = {'png', 'jpg', 'jpeg', 'gif'}


def _save_signature(file, old_filename=None):
    """Guarda imagen de firma y retorna el nombre del archivo."""
    if not file or file.filename == '':
        return old_filename
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_IMG:
        return old_filename
    filename = secure_filename(f'firma_{file.filename}')
    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
    return filename


def _apply_results_profile(usuario, form):
    """Crea o actualiza el UserResultProfile del usuario desde el formulario."""
    results_role = form.get('results_role', '').strip()
    professional_id = form.get('professional_id', '').strip()
    if not results_role:
        return
    if not usuario.results_profile:
        usuario.results_profile = UserResultProfile(user_id=usuario.id)
        db.session.add(usuario.results_profile)
    usuario.results_profile.role = results_role
    usuario.results_profile.professional_id = professional_id or None
    signature_file = request.files.get('signature_image')
    old = usuario.results_profile.signature_image
    saved = _save_signature(signature_file, old)
    if saved:
        usuario.results_profile.signature_image = saved


def admin_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash('No tienes permisos para acceder a esta sección.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def permiso_requerido(codigo):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.tiene_permiso(codigo):
                flash('No tienes permisos para esta acción.', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── USUARIOS ──────────────────────────────────────────────────────────────────

@admin_bp.route('/usuarios')
@login_required
@admin_requerido
def usuarios():
    lista = Usuario.query.order_by(Usuario.nombre).all()
    return render_template('admin/usuarios/lista.html', usuarios=lista)


@admin_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
@admin_requerido
def usuario_nuevo():
    modulos = Modulo.query.filter_by(activo=True).order_by(Modulo.orden).all()
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        rol = request.form.get('rol', 'operador')
        modulos_ids = request.form.getlist('modulos')

        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe.', 'danger')
        elif Usuario.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado.', 'danger')
        elif len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
        else:
            u = Usuario(username=username, nombre=nombre, email=email, rol=rol)
            u.set_password(password)
            if rol != 'admin':
                u.modulos = Modulo.query.filter(Modulo.id.in_(modulos_ids)).all()
            db.session.add(u)
            db.session.flush()
            _apply_results_profile(u, request.form)
            db.session.commit()
            flash(f'Usuario "{username}" creado correctamente.', 'success')
            return redirect(url_for('admin.usuarios'))

    return render_template('admin/usuarios/form.html', usuario=None, modulos=modulos)


@admin_bp.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_requerido
def usuario_editar(id):
    u = Usuario.query.get_or_404(id)
    modulos = Modulo.query.filter_by(activo=True).order_by(Modulo.orden).all()

    if request.method == 'POST':
        u.nombre = request.form.get('nombre', '').strip()
        u.email = request.form.get('email', '').strip()
        if u.username != 'EASY':
            u.rol = request.form.get('rol', 'operador')
            u.activo = request.form.get('activo') == 'on'
        modulos_ids = request.form.getlist('modulos')
        nueva_pass = request.form.get('password', '')

        if nueva_pass:
            if len(nueva_pass) < 6:
                flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
                return render_template('admin/usuarios/form.html', usuario=u, modulos=modulos)
            u.set_password(nueva_pass)

        if u.rol != 'admin':
            u.modulos = Modulo.query.filter(Modulo.id.in_(modulos_ids)).all()

        _apply_results_profile(u, request.form)
        db.session.commit()
        flash('Usuario actualizado correctamente.', 'success')
        return redirect(url_for('admin.usuarios'))

    return render_template('admin/usuarios/form.html', usuario=u, modulos=modulos)


@admin_bp.route('/usuarios/<int:id>/reset-password', methods=['GET', 'POST'])
@login_required
@admin_requerido
def usuario_reset_password(id):
    u = Usuario.query.get_or_404(id)
    if request.method == 'POST':
        nueva = request.form.get('password', '').strip()
        confirma = request.form.get('confirma', '').strip()
        if len(nueva) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
        elif nueva != confirma:
            flash('Las contraseñas no coinciden.', 'danger')
        else:
            u.set_password(nueva)
            db.session.commit()
            flash(f'Contraseña de "{u.username}" actualizada correctamente.', 'success')
            return redirect(url_for('admin.usuarios'))
    return render_template('admin/usuarios/reset_password.html', usuario=u)


@admin_bp.route('/usuarios/<int:id>/toggle')
@login_required
@admin_requerido
def usuario_toggle(id):
    u = Usuario.query.get_or_404(id)
    if u.username == 'EASY':
        flash('El usuario EASY no puede desactivarse.', 'warning')
    elif u.id == current_user.id:
        flash('No puedes desactivar tu propio usuario.', 'warning')
    else:
        u.activo = not u.activo
        db.session.commit()
        estado = 'activado' if u.activo else 'desactivado'
        flash(f'Usuario {estado} correctamente.', 'success')
    return redirect(url_for('admin.usuarios'))


# ── TABLAS PACIENTES ───────────────────────────────────────────────────────────

@admin_bp.route('/paises')
@login_required
def paises():
    lista = Pais.query.order_by(Pais.nombre).all()
    return render_template('admin/tablas/paises.html', paises=lista)


@admin_bp.route('/paises/guardar', methods=['POST'])
@login_required
def pais_guardar():
    id = request.form.get('id')
    codigo = request.form.get('codigo', '').strip().upper()
    nombre = request.form.get('nombre', '').strip()
    estado = request.form.get('estado') == 'on'

    if id:
        p = Pais.query.get_or_404(int(id))
        p.codigo = codigo
        p.nombre = nombre
        p.estado = estado
        flash('País actualizado.', 'success')
    else:
        p = Pais(codigo=codigo, nombre=nombre, estado=estado)
        db.session.add(p)
        flash('País creado.', 'success')
    db.session.commit()
    return redirect(url_for('admin.paises'))


@admin_bp.route('/departamentos')
@login_required
def departamentos():
    lista = Departamento.query.join(Pais).order_by(Pais.nombre, Departamento.nombre).all()
    paises_lista = Pais.query.filter_by(estado=True).order_by(Pais.nombre).all()
    return render_template('admin/tablas/departamentos.html',
                           departamentos=lista, paises=paises_lista)


@admin_bp.route('/departamentos/guardar', methods=['POST'])
@login_required
def departamento_guardar():
    id = request.form.get('id')
    codigo = request.form.get('codigo', '').strip().upper()
    nombre = request.form.get('nombre', '').strip()
    pais_id = request.form.get('pais_id')
    estado = request.form.get('estado') == 'on'

    if id:
        d = Departamento.query.get_or_404(int(id))
        d.codigo = codigo
        d.nombre = nombre
        d.pais_id = pais_id
        d.estado = estado
        flash('Departamento actualizado.', 'success')
    else:
        d = Departamento(codigo=codigo, nombre=nombre, pais_id=pais_id, estado=estado)
        db.session.add(d)
        flash('Departamento creado.', 'success')
    db.session.commit()
    return redirect(url_for('admin.departamentos'))


@admin_bp.route('/municipios')
@login_required
def municipios():
    lista = Municipio.query.join(Departamento).order_by(Departamento.nombre, Municipio.nombre).all()
    deptos = Departamento.query.filter_by(estado=True).order_by(Departamento.nombre).all()
    return render_template('admin/tablas/municipios.html', municipios=lista, departamentos=deptos)


@admin_bp.route('/municipios/guardar', methods=['POST'])
@login_required
def municipio_guardar():
    id = request.form.get('id')
    codigo = request.form.get('codigo', '').strip().upper()
    nombre = request.form.get('nombre', '').strip()
    departamento_id = request.form.get('departamento_id')
    es_localidad = request.form.get('es_localidad') == 'on'
    estado = request.form.get('estado') == 'on'

    if id:
        m = Municipio.query.get_or_404(int(id))
        m.codigo = codigo
        m.nombre = nombre
        m.departamento_id = departamento_id
        m.es_localidad = es_localidad
        m.estado = estado
        flash('Municipio/Localidad actualizado.', 'success')
    else:
        m = Municipio(codigo=codigo, nombre=nombre, departamento_id=departamento_id,
                      es_localidad=es_localidad, estado=estado)
        db.session.add(m)
        flash('Municipio/Localidad creado.', 'success')
    db.session.commit()
    return redirect(url_for('admin.municipios'))


@admin_bp.route('/tipos-identificacion')
@login_required
def tipos_identificacion():
    lista = TipoIdentificacion.query.order_by(TipoIdentificacion.nombre).all()
    return render_template('admin/tablas/tipos_identificacion.html', tipos=lista)


@admin_bp.route('/tipos-identificacion/guardar', methods=['POST'])
@login_required
def tipo_identificacion_guardar():
    id = request.form.get('id')
    codigo = request.form.get('codigo', '').strip().upper()
    nombre = request.form.get('nombre', '').strip()
    estado = request.form.get('estado') == 'on'
    if id:
        t = TipoIdentificacion.query.get_or_404(int(id))
        t.codigo = codigo; t.nombre = nombre; t.estado = estado
        flash('Tipo de identificación actualizado.', 'success')
    else:
        t = TipoIdentificacion(codigo=codigo, nombre=nombre, estado=estado)
        db.session.add(t)
        flash('Tipo de identificación creado.', 'success')
    db.session.commit()
    return redirect(url_for('admin.tipos_identificacion'))


@admin_bp.route('/tipos-usuario-paciente')
@login_required
def tipos_usuario_paciente():
    lista = TipoUsuarioPaciente.query.order_by(TipoUsuarioPaciente.nombre).all()
    return render_template('admin/tablas/tipos_usuario_paciente.html', tipos=lista)


@admin_bp.route('/tipos-usuario-paciente/guardar', methods=['POST'])
@login_required
def tipo_usuario_paciente_guardar():
    id = request.form.get('id')
    codigo = request.form.get('codigo', '').strip().upper()
    nombre = request.form.get('nombre', '').strip()
    estado = request.form.get('estado') == 'on'
    if id:
        t = TipoUsuarioPaciente.query.get_or_404(int(id))
        t.codigo = codigo; t.nombre = nombre; t.estado = estado
        flash('Tipo de usuario actualizado.', 'success')
    else:
        t = TipoUsuarioPaciente(codigo=codigo, nombre=nombre, estado=estado)
        db.session.add(t)
        flash('Tipo de usuario creado.', 'success')
    db.session.commit()
    return redirect(url_for('admin.tipos_usuario_paciente'))


@admin_bp.route('/sexos')
@login_required
def sexos():
    lista = Sexo.query.order_by(Sexo.nombre).all()
    return render_template('admin/tablas/sexos.html', sexos=lista)


@admin_bp.route('/sexos/guardar', methods=['POST'])
@login_required
def sexo_guardar():
    id = request.form.get('id')
    codigo = request.form.get('codigo', '').strip().upper()
    nombre = request.form.get('nombre', '').strip()
    if id:
        s = Sexo.query.get_or_404(int(id))
        s.codigo = codigo; s.nombre = nombre
        flash('Sexo actualizado.', 'success')
    else:
        s = Sexo(codigo=codigo, nombre=nombre)
        db.session.add(s)
        flash('Sexo creado.', 'success')
    db.session.commit()
    return redirect(url_for('admin.sexos'))


@admin_bp.route('/formas-pago')
@login_required
def formas_pago():
    lista = FormaPago.query.order_by(FormaPago.nombre).all()
    return render_template('admin/tablas/formas_pago.html', formas=lista)


@admin_bp.route('/formas-pago/guardar', methods=['POST'])
@login_required
def forma_pago_guardar():
    id = request.form.get('id')
    codigo = request.form.get('codigo', '').strip().upper()
    nombre = request.form.get('nombre', '').strip()
    estado = request.form.get('estado') == 'on'
    if id:
        f = FormaPago.query.get_or_404(int(id))
        f.codigo = codigo; f.nombre = nombre; f.estado = estado
        flash('Forma de pago actualizada.', 'success')
    else:
        f = FormaPago(codigo=codigo, nombre=nombre, estado=estado)
        db.session.add(f)
        flash('Forma de pago creada.', 'success')
    db.session.commit()
    return redirect(url_for('admin.formas_pago'))


# ── NUMERACIÓN ────────────────────────────────────────────────────────────────

@admin_bp.route('/numeracion')
@login_required
@admin_requerido
def numeracion():
    lista = NumeracionInicial.query.order_by(NumeracionInicial.anio.desc()).all()
    return render_template('admin/numeracion.html', numeraciones=lista)


@admin_bp.route('/numeracion/guardar', methods=['POST'])
@login_required
@admin_requerido
def numeracion_guardar():
    id = request.form.get('id')
    anio = int(request.form.get('anio', 0))
    if id:
        n = NumeracionInicial.query.get_or_404(int(id))
    else:
        if NumeracionInicial.query.filter_by(anio=anio).first():
            flash(f'Ya existe numeración para el año {anio}.', 'danger')
            return redirect(url_for('admin.numeracion'))
        n = NumeracionInicial(anio=anio)
        db.session.add(n)

    n.anio = anio
    n.prefijo_atencion = request.form.get('prefijo_atencion', '').strip()
    n.consecutivo_atencion = int(request.form.get('consecutivo_atencion', 1))
    n.prefijo_prefactura = request.form.get('prefijo_prefactura', 'PF').strip()
    n.consecutivo_prefactura = int(request.form.get('consecutivo_prefactura', 1))
    n.prefijo_recibo = request.form.get('prefijo_recibo', 'RC').strip()
    n.consecutivo_recibo = int(request.form.get('consecutivo_recibo', 1))
    db.session.commit()
    flash('Numeración guardada correctamente.', 'success')
    return redirect(url_for('admin.numeracion'))


# ── AJAX helpers ──────────────────────────────────────────────────────────────

@admin_bp.route('/api/departamentos-por-pais/<int:pais_id>')
@login_required
def api_departamentos_por_pais(pais_id):
    deptos = Departamento.query.filter_by(pais_id=pais_id, estado=True).order_by(Departamento.nombre).all()
    return jsonify([{'id': d.id, 'nombre': d.nombre} for d in deptos])


@admin_bp.route('/api/municipios-por-depto/<int:depto_id>')
@login_required
def api_municipios_por_depto(depto_id):
    munis = Municipio.query.filter_by(departamento_id=depto_id, estado=True).order_by(Municipio.nombre).all()
    return jsonify([{'id': m.id, 'nombre': m.nombre, 'es_localidad': m.es_localidad} for m in munis])


# ── PERSONAS QUE ATIENDEN ─────────────────────────────────────────────────────

@admin_bp.route('/personas-atienden')
@login_required
def personas_atienden():
    lista = PersonaAtiende.query.order_by(PersonaAtiende.apellidos, PersonaAtiende.nombres).all()
    return render_template('admin/tablas/personas_atienden.html', personas=lista)


@admin_bp.route('/personas-atienden/guardar', methods=['POST'])
@login_required
def persona_atiende_guardar():
    id = request.form.get('id')
    tipo_id = request.form.get('tipo_identificacion', 'CC').strip().upper()
    identificacion = request.form.get('identificacion', '').strip()
    nombres = request.form.get('nombres', '').strip()
    apellidos = request.form.get('apellidos', '').strip()
    cargo = request.form.get('cargo', '').strip()
    celular = request.form.get('celular', '').strip()
    estado = request.form.get('estado') == 'on'

    if not identificacion or not nombres or not apellidos:
        flash('Identificación, nombres y apellidos son obligatorios.', 'danger')
        return redirect(url_for('admin.personas_atienden'))

    if id:
        p = PersonaAtiende.query.get_or_404(int(id))
        p.tipo_identificacion = tipo_id
        p.identificacion = identificacion
        p.nombres = nombres
        p.apellidos = apellidos
        p.cargo = cargo
        p.celular = celular
        p.estado = estado
        flash('Persona actualizada.', 'success')
    else:
        if PersonaAtiende.query.filter_by(identificacion=identificacion).first():
            flash(f'Ya existe una persona con identificación {identificacion}.', 'danger')
            return redirect(url_for('admin.personas_atienden'))
        p = PersonaAtiende(tipo_identificacion=tipo_id, identificacion=identificacion,
                           nombres=nombres, apellidos=apellidos,
                           cargo=cargo, celular=celular, estado=estado)
        db.session.add(p)
        flash('Persona registrada.', 'success')

    db.session.commit()
    return redirect(url_for('admin.personas_atienden'))


@admin_bp.route('/personas-atienden/<int:id>/toggle')
@login_required
def persona_atiende_toggle(id):
    p = PersonaAtiende.query.get_or_404(id)
    p.estado = not p.estado
    db.session.commit()
    flash(f'Persona {"activada" if p.estado else "desactivada"}.', 'success')
    return redirect(url_for('admin.personas_atienden'))


@admin_bp.route('/api/personas-atienden')
@login_required
def api_personas_atienden():
    """API para el select del formulario de atenciones"""
    personas = PersonaAtiende.query.filter_by(estado=True).order_by(
        PersonaAtiende.apellidos, PersonaAtiende.nombres).all()
    return jsonify([{
        'id': p.id,
        'nombre_completo': p.nombre_completo,
        'cargo': p.cargo or '',
        'identificacion': p.identificacion
    } for p in personas])
