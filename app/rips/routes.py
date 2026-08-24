from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required
from app import db
from app.models import AtencionEncabezado, AtencionDetalle, ConfigRips, Cups, Cliente
from app.rips import rips_bp
import json
import io
from datetime import datetime


def _generar_json_rips(atenciones, num_factura, tipo_usuario_override=None):
    """Genera el JSON de RIPS según el formato del Ministerio de Salud Colombia."""
    config = ConfigRips.query.first()
    if not config:
        return None, 'Debe configurar los datos RIPS antes de generar.'

    cups_transporte = config.cups_transporte
    consecutivo_usuario = 0
    # Tipo de usuario: prioridad override > config
    tipo_usuario = tipo_usuario_override or config.tipo_usuario_rips or '12'

    usuarios = []

    for atencion in atenciones:
        p = atencion.paciente
        if not p:
            continue

        consecutivo_usuario += 1
        consecutivo_proc = 0
        procedimientos = []

        for detalle in atencion.detalles:
            consecutivo_proc += 1
            valor_cop = float(detalle.valor)
            # Si es transporte (890105), descontar lo pagado por el paciente
            if detalle.cups_codigo == cups_transporte or detalle.cups_codigo == '890105':
                valor_cop = max(0, valor_cop - float(atencion.abono_cliente or 0))
                # Si queda en cero o negativo, no incluir este registro
                if valor_cop <= 0:
                    consecutivo_proc -= 1
                    continue

            proc = {
                "codPrestador": config.codigo_habilitacion or '',
                "fechaInicioAtencion": atencion.fecha_hora_ingreso.strftime('%Y-%m-%d %H:%M')
                    if atencion.fecha_hora_ingreso else str(atencion.fecha_atencion) + ' 09:00',
                "idMIPRES": None,
                "numAutorizacion": atencion.autorizacion_transporte
                    if detalle.cups_codigo == cups_transporte
                    else (atencion.autorizacion or ''),
                "codProcedimiento": detalle.cups_codigo,
                "viaIngresoServicioSalud": (config.via_ingreso or '02').zfill(2),
                "modalidadGrupoServicioTecSal": (config.modalidad_atencion or '03').zfill(2),
                "grupoServicios": (config.grupo_servicios or '02').zfill(2),
                "codServicio": int(config.cod_servicio or 739),
                "finalidadTecnologiaSalud": (config.finalidad_tecnologia or '15').zfill(2),
                "tipoDocumentoIdentificacion": config.tipo_doc_prestador or 'CC',
                "numDocumentoIdentificacion": config.num_doc_prestador or '',
                "codDiagnosticoPrincipal": config.cod_diagnostico_principal or 'Z000',
                "codDiagnosticoRelacionado": None,
                "codComplicacion": None,
                "vrServicio": int(valor_cop),
                "conceptoRecaudo": (config.concepto_recaudo or '05').zfill(2),
                "valorPagoModerador": 0,
                "numFEVPagoModerador": None,
                "codDiagnosticoPrincipalCIE11": None,
                "nomCodDiagnosticoPrincipalCIE11": None,
                "codDiagnosticoRelacionadoCIE11": None,
                "nomCodDiagnosticoRelacionadoCIE11": None,
                "codComplicacionCIE11": None,
                "nomCodComplicacionCIE11": None,
                "codigoVIDA": None,
                "consecutivo": consecutivo_proc
            }
            procedimientos.append(proc)

        usuario = {
            "tipoDocumentoIdentificacion": p.tipo_id.codigo if p.tipo_id else 'CC',
            "numDocumentoIdentificacion": p.identificacion,
            "tipoUsuario": tipo_usuario,
            "fechaNacimiento": str(p.fecha_nacimiento),
            "codSexo": p.sexo.codigo if p.sexo else 'M',
            "codPaisResidencia": p.pais_residencia.codigo if p.pais_residencia else '170',
            "codMunicipioResidencia": p.municipio.codigo if p.municipio else '11001',
            "codZonaTerritorialResidencia": (config.zona_territorial or '02').zfill(2),
            "incapacidad": "NO",
            "codPaisOrigen": p.pais_nacimiento.codigo if p.pais_nacimiento else '170',
            "registroSIRAS": None,
            "consecutivo": consecutivo_usuario,
            "servicios": {
                "procedimientos": procedimientos
            }
        }
        usuarios.append(usuario)

    rips = {
        "numDocumentoIdObligado": config.nit_facturador or '',
        "numFactura": num_factura,
        "tipoNota": None,
        "numNota": None,
        "usuarios": usuarios
    }

    return rips, None


@rips_bp.route('/configuracion', methods=['GET', 'POST'])
@login_required
def configuracion():
    config = ConfigRips.query.first()
    cups_transporte_list = Cups.query.filter_by(es_transporte=True, estado=True).all()

    if request.method == 'POST':
        if not config:
            config = ConfigRips()
            db.session.add(config)

        config.nit_facturador = request.form.get('nit_facturador', '').strip()
        config.razon_social = request.form.get('razon_social', '').strip()
        config.codigo_habilitacion = request.form.get('codigo_habilitacion', '').strip()
        config.cups_transporte = request.form.get('cups_transporte') or None
        config.tipo_usuario_rips = request.form.get('tipo_usuario_rips', '11').strip()
        config.modalidad_atencion = request.form.get('modalidad_atencion', '03').strip()
        config.ambito_atencion = request.form.get('ambito_atencion', '1').strip()
        config.via_ingreso = request.form.get('via_ingreso', '02').strip()
        config.grupo_servicios = request.form.get('grupo_servicios', '02').strip()
        config.cod_servicio = request.form.get('cod_servicio', '739').strip()
        config.finalidad_tecnologia = request.form.get('finalidad_tecnologia', '15').strip()
        config.concepto_recaudo = request.form.get('concepto_recaudo', '05').strip()
        config.zona_territorial = request.form.get('zona_territorial', '02').strip()
        config.tipo_doc_prestador = request.form.get('tipo_doc_prestador', 'CC').strip()
        config.num_doc_prestador = request.form.get('num_doc_prestador', '').strip()
        config.cod_diagnostico_principal = request.form.get('cod_diagnostico_principal', 'Z000').strip()
        db.session.commit()
        flash('Configuración RIPS guardada.', 'success')
        return redirect(url_for('rips.configuracion'))

    return render_template('rips/configuracion.html', config=config,
                           cups_transporte_list=cups_transporte_list)


@rips_bp.route('/generar', methods=['GET', 'POST'])
@login_required
def generar():
    if request.method == 'POST':
        num_factura = request.form.get('num_factura', '').strip()
        fecha_desde_str = request.form.get('fecha_desde', '')
        fecha_hasta_str = request.form.get('fecha_hasta', '')
        cliente_id = request.form.get('cliente_id')
        tipo_usuario_override = request.form.get('tipo_usuario_override', '').strip() or None
        atenciones_rips = request.form.getlist('atenciones_rips')

        if not num_factura:
            flash('El número de factura es obligatorio.', 'danger')
            return redirect(url_for('rips.generar'))

        if not cliente_id:
            flash('Debe seleccionar un cliente.', 'danger')
            return redirect(url_for('rips.generar'))

        try:
            fd = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date()
            fh = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Fechas inválidas.', 'danger')
            return redirect(url_for('rips.generar'))

        # Si es PARTICULAR y hay selección de atenciones
        if atenciones_rips:
            atenciones = AtencionEncabezado.query.filter(
                AtencionEncabezado.nro_consecutivo.in_(atenciones_rips)
            ).all()
        else:
            atenciones = AtencionEncabezado.query.filter(
                AtencionEncabezado.cliente_id == cliente_id,
                AtencionEncabezado.fecha_atencion >= fd,
                AtencionEncabezado.fecha_atencion <= fh,
                AtencionEncabezado.estado.in_(['Prefacturado', 'Ingresado'])
            ).all()

        if not atenciones:
            flash('No hay atenciones para los criterios seleccionados.', 'warning')
            return redirect(url_for('rips.generar'))

        rips_data, error = _generar_json_rips(atenciones, num_factura, tipo_usuario_override)
        if error:
            flash(error, 'danger')
            return redirect(url_for('rips.generar'))

        json_str = json.dumps(rips_data, ensure_ascii=False, indent=2)
        buf = io.BytesIO(json_str.encode('utf-8'))
        filename = f'RIPS_{num_factura}_{fd}_{fh}.json'
        return send_file(buf, mimetype='application/json',
                         as_attachment=True, download_name=filename)

    clientes = Cliente.query.filter_by(estado=True).order_by(Cliente.nombre).all()
    return render_template('rips/generar.html', clientes=clientes)


@rips_bp.route('/api/atenciones-periodo')
@login_required
def api_atenciones_periodo():
    """API para buscar atenciones de PARTICULAR en un rango."""
    cliente_id = request.args.get('cliente_id')
    fecha_desde_str = request.args.get('fecha_desde', '')
    fecha_hasta_str = request.args.get('fecha_hasta', '')

    if not cliente_id or not fecha_desde_str or not fecha_hasta_str:
        return jsonify([])

    try:
        fd = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date()
        fh = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify([])

    atenciones = AtencionEncabezado.query.filter(
        AtencionEncabezado.cliente_id == cliente_id,
        AtencionEncabezado.fecha_atencion >= fd,
        AtencionEncabezado.fecha_atencion <= fh,
        AtencionEncabezado.estado.in_(['Prefacturado', 'Ingresado'])
    ).order_by(AtencionEncabezado.fecha_atencion).all()

    return jsonify([{
        'consecutivo': a.nro_consecutivo,
        'paciente': a.paciente.nombre_completo if a.paciente else a.paciente_id,
        'fecha': str(a.fecha_atencion),
        'valor': float(a.valor_total)
    } for a in atenciones])
