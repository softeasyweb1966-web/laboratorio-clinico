from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import date, datetime
from app import db
from app.models import (AtencionEncabezado, AtencionDetalle, Paciente, Cliente,
                        Cups, FormaPago, NumeracionInicial, ConfigRips,
                        PersonaAtiende)
from app.atenciones import atenciones_bp


def _generar_consecutivo():
    """Genera el próximo número de consecutivo para el año actual."""
    anio = date.today().year
    num = NumeracionInicial.query.filter_by(anio=anio).first()
    if not num:
        # Crear numeración automática si no existe
        num = NumeracionInicial(anio=anio, prefijo_atencion='', consecutivo_atencion=1,
                                prefijo_prefactura='PF', consecutivo_prefactura=1,
                                prefijo_recibo='RC', consecutivo_recibo=1)
        db.session.add(num)
        db.session.flush()

    consecutivo = f'{num.prefijo_atencion}{anio}{num.consecutivo_atencion:06d}'
    num.consecutivo_atencion += 1
    return consecutivo


@atenciones_bp.route('/')
@login_required
def lista():
    q = request.args.get('q', '').strip()
    estado = request.args.get('estado', '')
    query = AtencionEncabezado.query
    if q:
        query = query.filter(
            db.or_(
                AtencionEncabezado.nro_consecutivo.ilike(f'%{q}%'),
                AtencionEncabezado.paciente_id.ilike(f'%{q}%')
            )
        )
    if estado:
        query = query.filter_by(estado=estado)
    atenciones = query.order_by(AtencionEncabezado.fecha_hora_ingreso.desc()).limit(200).all()
    return render_template('atenciones/lista.html', atenciones=atenciones, q=q, estado=estado)


@atenciones_bp.route('/hoja-trabajo')
@login_required
def hoja_trabajo():
    fecha_desde = request.args.get('fecha_desde', str(date.today()))
    fecha_hasta = request.args.get('fecha_hasta', str(date.today()))
    estado = request.args.get('estado', 'Ingresado').strip()
    cliente_id = request.args.get('cliente_id', '').strip()

    clientes = Cliente.query.filter_by(estado=True).order_by(Cliente.nombre).all()
    atenciones = []

    try:
        fd = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
        fh = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
        query = AtencionEncabezado.query.filter(
            AtencionEncabezado.fecha_atencion >= fd,
            AtencionEncabezado.fecha_atencion <= fh
        )
        if estado:
            query = query.filter_by(estado=estado)
        if cliente_id:
            query = query.filter_by(cliente_id=cliente_id)
        atenciones = query.order_by(
            AtencionEncabezado.fecha_atencion.asc(),
            AtencionEncabezado.fecha_hora_ingreso.asc()
        ).all()
    except ValueError:
        flash('Las fechas de la hoja de trabajo no son válidas.', 'danger')

    return render_template(
        'atenciones/hoja_trabajo.html',
        atenciones=atenciones,
        clientes=clientes,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        estado=estado,
        cliente_id=cliente_id
    )


@atenciones_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def nueva():
    formas_pago = FormaPago.query.filter_by(estado=True).order_by(FormaPago.nombre).all()
    personas = PersonaAtiende.query.filter_by(estado=True).order_by(
        PersonaAtiende.apellidos, PersonaAtiende.nombres).all()

    if request.method == 'POST':
        paciente_id = request.form.get('paciente_id', '').strip()
        cliente_id = request.form.get('cliente_id')
        fecha_str = request.form.get('fecha_atencion', str(date.today()))
        autorizacion = request.form.get('autorizacion', '').strip()
        autorizacion_transporte = request.form.get('autorizacion_transporte', '').strip()
        persona_atiende_id = request.form.get('persona_atiende_id') or None
        forma_pago_id = request.form.get('forma_pago_id') or None
        abono = float(request.form.get('abono_cliente', 0) or 0)
        forma_abono_id = request.form.get('forma_abono_id') or None

        cups_codigos = request.form.getlist('cups_codigo[]')
        cups_valores = request.form.getlist('cups_valor[]')

        if not paciente_id or not cliente_id or not cups_codigos:
            flash('Paciente, empresa y al menos un examen son obligatorios.', 'danger')
            return render_template('atenciones/form.html', formas_pago=formas_pago, personas=personas)

        try:
            fecha_atencion = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Fecha de atención inválida.', 'danger')
            return render_template('atenciones/form.html', formas_pago=formas_pago, personas=personas)

        consecutivo = _generar_consecutivo()
        valor_total = sum(float(v or 0) for v in cups_valores)
        saldo_empresa = max(0, valor_total - abono)

        atencion = AtencionEncabezado(
            nro_consecutivo=consecutivo,
            cliente_id=cliente_id,
            paciente_id=paciente_id,
            fecha_atencion=fecha_atencion,
            autorizacion=autorizacion,
            autorizacion_transporte=autorizacion_transporte,
            persona_atiende_id=persona_atiende_id,
            forma_pago_id=forma_pago_id,
            abono_cliente=abono,
            forma_abono_id=forma_abono_id,
            saldo_empresa=saldo_empresa,
            estado='Ingresado',
            usuario_ingresa_id=current_user.id
        )
        db.session.add(atencion)

        for i, (codigo, valor_str) in enumerate(zip(cups_codigos, cups_valores), start=1):
            if codigo:
                detalle = AtencionDetalle(
                    nro_consecutivo=consecutivo,
                    secuencia=i,
                    cups_codigo=codigo,
                    valor=float(valor_str or 0)
                )
                db.session.add(detalle)

        db.session.commit()
        flash(f'Atención registrada con consecutivo {consecutivo}.', 'success')
        return redirect(url_for('atenciones.ver', consecutivo=consecutivo))

    return render_template('atenciones/form.html', formas_pago=formas_pago, personas=personas)


@atenciones_bp.route('/<consecutivo>')
@login_required
def ver(consecutivo):
    a = AtencionEncabezado.query.get_or_404(consecutivo)
    return render_template('atenciones/ver.html', atencion=a)


@atenciones_bp.route('/<consecutivo>/anular', methods=['POST'])
@login_required
def anular(consecutivo):
    a = AtencionEncabezado.query.get_or_404(consecutivo)
    if a.estado == 'Prefacturado':
        flash('No se puede anular una atención prefacturada.', 'danger')
    else:
        a.estado = 'Anulado'
        db.session.commit()
        flash(f'Atención {consecutivo} anulada.', 'warning')
    return redirect(url_for('atenciones.lista'))


@atenciones_bp.route('/api/info-paciente/<identificacion>')
@login_required
def api_info_paciente(identificacion):
    p = Paciente.query.get(identificacion)
    if not p:
        return jsonify({'existe': False})

    # Buscar la última atención del paciente para traer la empresa
    ultima = AtencionEncabezado.query.filter_by(
        paciente_id=identificacion
    ).filter(
        AtencionEncabezado.estado != 'Anulado'
    ).order_by(AtencionEncabezado.fecha_hora_ingreso.desc()).first()

    ultima_empresa = None
    if ultima and ultima.cliente:
        ultima_empresa = {
            'id': ultima.cliente.id,
            'codigo': ultima.cliente.codigo,
            'nombre': ultima.cliente.nombre,
            'fecha': str(ultima.fecha_atencion),
            'consecutivo': ultima.nro_consecutivo
        }

    return jsonify({
        'existe': True,
        'identificacion': p.identificacion,
        'nombre_completo': p.nombre_completo,
        'tipo_id': p.tipo_id.codigo if p.tipo_id else '',
        'fecha_nacimiento': str(p.fecha_nacimiento),
        'sexo': p.sexo.nombre if p.sexo else '',
        'ultima_empresa': ultima_empresa
    })


@atenciones_bp.route('/api/cups-cliente/<int:cliente_id>')
@login_required
def api_cups_cliente(cliente_id):
    """Retorna los CUPS disponibles para un cliente (lista de precios o general)"""
    from app.models import ListaPrecioItem
    cliente = Cliente.query.get(cliente_id)

    if cliente and cliente.lista_precio_id:
        # Cliente con lista de precios: traer solo esos
        items = ListaPrecioItem.query.filter_by(lista_id=cliente.lista_precio_id).join(Cups).filter(
            Cups.estado == True
        ).order_by(Cups.descripcion).all()
        result = [{'codigo': i.cups_codigo,
                   'descripcion': i.cups.descripcion,
                   'valor': float(i.valor),
                   'es_transporte': i.cups.es_transporte}
                  for i in items]
    else:
        # Sin lista: traer todos los CUPS activos
        cups_todos = Cups.query.filter_by(estado=True).order_by(Cups.descripcion).all()
        result = [{'codigo': c.codigo, 'descripcion': c.descripcion,
                   'valor': float(c.valor), 'es_transporte': c.es_transporte}
                  for c in cups_todos]
    return jsonify(result)
