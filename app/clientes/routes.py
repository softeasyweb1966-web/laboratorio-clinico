from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
import unicodedata
from app import db
from app.models import Cliente, Cups, TarifaCliente, Pais, Municipio, Departamento, ListaPrecio
from app.clientes import clientes_bp


def _generar_codigo(nombre):
    """Genera código de 6 letras desde el nombre del cliente."""
    nfkd = unicodedata.normalize('NFKD', nombre.upper())
    limpio = ''.join(c for c in nfkd if not unicodedata.combining(c))
    solo_alfanum = ''.join(c for c in limpio if c.isalnum())
    base = solo_alfanum[:6]
    candidato = base
    sufijo = 1
    while Cliente.query.filter_by(codigo=candidato).first():
        candidato = base[:5] + str(sufijo)
        sufijo += 1
    return candidato


def _build_form_data(cliente=None):
    if request.method == 'POST':
        return {
            'codigo': request.form.get('codigo', '').strip().upper(),
            'nombre': request.form.get('nombre', '').strip(),
            'tipo_identificacion': request.form.get('tipo_identificacion', '').strip(),
            'nro_identificacion': request.form.get('nro_identificacion', '').strip(),
            'lista_precio_id': request.form.get('lista_precio_id', '').strip(),
            'codigo_tarifa': request.form.get('codigo_tarifa', '').strip(),
            'porcentaje_iva': request.form.get('porcentaje_iva', '0').strip() or '0',
            'porcentaje_retfte': request.form.get('porcentaje_retfte', '0').strip() or '0',
            'pais_id': request.form.get('pais_id', '').strip(),
            'departamento_id': request.form.get('departamento_id', '').strip(),
            'municipio_id': request.form.get('municipio_id', '').strip(),
            'direccion': request.form.get('direccion', '').strip(),
            'telefono': request.form.get('telefono', '').strip(),
            'email': request.form.get('email', '').strip(),
            'contacto_facturacion': request.form.get('contacto_facturacion', '').strip(),
            'dir_facturacion': request.form.get('dir_facturacion', '').strip(),
            'tel_facturacion': request.form.get('tel_facturacion', '').strip(),
            'email_facturacion': request.form.get('email_facturacion', '').strip(),
            'contacto_administrativo': request.form.get('contacto_administrativo', '').strip(),
            'dir_administrativo': request.form.get('dir_administrativo', '').strip(),
            'tel_administrativo': request.form.get('tel_administrativo', '').strip(),
            'email_administrativo': request.form.get('email_administrativo', '').strip(),
            'estado': request.form.get('estado') == 'on'
        }

    municipio = cliente.municipio if cliente else None
    return {
        'codigo': cliente.codigo if cliente else '',
        'nombre': cliente.nombre if cliente else '',
        'tipo_identificacion': cliente.tipo_identificacion if cliente else '',
        'nro_identificacion': cliente.nro_identificacion if cliente else '',
        'lista_precio_id': str(cliente.lista_precio_id) if cliente and cliente.lista_precio_id else '',
        'codigo_tarifa': cliente.codigo_tarifa if cliente else '',
        'porcentaje_iva': str(cliente.porcentaje_iva or 0) if cliente else '0',
        'porcentaje_retfte': str(cliente.porcentaje_retfte or 0) if cliente else '0',
        'pais_id': str(cliente.pais_id) if cliente and cliente.pais_id else '',
        'departamento_id': str(municipio.departamento_id) if municipio else '',
        'municipio_id': str(cliente.municipio_id) if cliente and cliente.municipio_id else '',
        'direccion': cliente.direccion if cliente else '',
        'telefono': cliente.telefono if cliente else '',
        'email': cliente.email if cliente else '',
        'contacto_facturacion': cliente.contacto_facturacion if cliente else '',
        'dir_facturacion': cliente.dir_facturacion if cliente else '',
        'tel_facturacion': cliente.tel_facturacion if cliente else '',
        'email_facturacion': cliente.email_facturacion if cliente else '',
        'contacto_administrativo': cliente.contacto_administrativo if cliente else '',
        'dir_administrativo': cliente.dir_administrativo if cliente else '',
        'tel_administrativo': cliente.tel_administrativo if cliente else '',
        'email_administrativo': cliente.email_administrativo if cliente else '',
        'estado': cliente.estado if cliente else True
    }


@clientes_bp.route('/')
@login_required
def lista():
    q = request.args.get('q', '').strip()
    query = Cliente.query
    if q:
        query = query.filter(
            db.or_(
                Cliente.codigo.ilike(f'%{q}%'),
                Cliente.nombre.ilike(f'%{q}%'),
                Cliente.nro_identificacion.ilike(f'%{q}%')
            )
        )
    clientes = query.order_by(Cliente.nombre).limit(200).all()
    return render_template('clientes/lista.html', clientes=clientes, q=q)


@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    return _form_cliente(None)


@clientes_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    c = Cliente.query.get_or_404(id)
    return _form_cliente(c)


def _form_cliente(cliente):
    form_data = _build_form_data(cliente)
    paises = Pais.query.filter_by(estado=True).order_by(Pais.nombre).all()
    departamentos = []
    municipios = []
    lista_precio_seleccionada = None

    if form_data['pais_id']:
        departamentos = Departamento.query.filter_by(
            pais_id=form_data['pais_id'], estado=True
        ).order_by(Departamento.nombre).all()
    if form_data['departamento_id']:
        municipios = Municipio.query.filter_by(
            departamento_id=form_data['departamento_id'], estado=True
        ).order_by(Municipio.nombre).all()
    if form_data['lista_precio_id']:
        lista_precio_seleccionada = ListaPrecio.query.get(form_data['lista_precio_id'])

    if request.method == 'POST':
        codigo = request.form.get('codigo', '').strip().upper()
        nombre = request.form.get('nombre', '').strip()

        if not codigo or not nombre:
            flash('Código y nombre son obligatorios.', 'danger')
        else:
            if cliente is None:
                if Cliente.query.filter_by(codigo=codigo).first():
                    flash(f'Ya existe un cliente con el código {codigo}.', 'danger')
                    return render_template(
                        'clientes/form.html',
                        cliente=None,
                        paises=paises,
                        departamentos=departamentos,
                        municipios=municipios,
                        form_data=form_data,
                        lista_precio_seleccionada=lista_precio_seleccionada
                    )
                c = Cliente(codigo=codigo, usuario_crea_id=current_user.id)
                db.session.add(c)
            else:
                c = cliente

            c.codigo = codigo
            c.nombre = nombre
            c.tipo_identificacion = request.form.get('tipo_identificacion', '').strip()
            c.nro_identificacion = request.form.get('nro_identificacion', '').strip()
            c.pais_id = request.form.get('pais_id') or None
            c.municipio_id = request.form.get('municipio_id') or None
            c.direccion = request.form.get('direccion', '').strip()
            c.telefono = request.form.get('telefono', '').strip()
            c.email = request.form.get('email', '').strip()
            c.contacto_facturacion = request.form.get('contacto_facturacion', '').strip()
            c.dir_facturacion = request.form.get('dir_facturacion', '').strip()
            c.tel_facturacion = request.form.get('tel_facturacion', '').strip()
            c.email_facturacion = request.form.get('email_facturacion', '').strip()
            c.contacto_administrativo = request.form.get('contacto_administrativo', '').strip()
            c.dir_administrativo = request.form.get('dir_administrativo', '').strip()
            c.tel_administrativo = request.form.get('tel_administrativo', '').strip()
            c.email_administrativo = request.form.get('email_administrativo', '').strip()
            c.porcentaje_iva = float(request.form.get('porcentaje_iva', 0) or 0)
            c.porcentaje_retfte = float(request.form.get('porcentaje_retfte', 0) or 0)
            c.codigo_tarifa = request.form.get('codigo_tarifa', '').strip()
            lista_precio_id = request.form.get('lista_precio_id') or None
            c.lista_precio_id = int(lista_precio_id) if lista_precio_id else None
            c.estado = request.form.get('estado') == 'on'

            db.session.commit()
            flash('Cliente guardado correctamente.', 'success')
            return redirect(url_for('clientes.lista'))

    return render_template(
        'clientes/form.html',
        cliente=cliente,
        paises=paises,
        departamentos=departamentos,
        municipios=municipios,
        form_data=form_data,
        lista_precio_seleccionada=lista_precio_seleccionada
    )


@clientes_bp.route('/<int:id>/tarifa', methods=['GET', 'POST'])
@login_required
def tarifa(id):
    cliente = Cliente.query.get_or_404(id)
    cups_todos = Cups.query.filter_by(estado=True).order_by(Cups.descripcion).all()

    if request.method == 'POST':
        TarifaCliente.query.filter_by(cliente_id=id).delete()
        for cups in cups_todos:
            valor_str = request.form.get(f'valor_{cups.codigo}', '').strip()
            if valor_str:
                try:
                    valor = float(valor_str)
                    t = TarifaCliente(cliente_id=id, cups_codigo=cups.codigo, valor=valor)
                    db.session.add(t)
                except ValueError:
                    pass
        db.session.commit()
        flash('Tarifa actualizada correctamente.', 'success')
        return redirect(url_for('clientes.lista'))

    tarifas_dict = {t.cups_codigo: t.valor for t in cliente.tarifas}
    return render_template('clientes/tarifa.html', cliente=cliente,
                           cups_todos=cups_todos, tarifas_dict=tarifas_dict)


@clientes_bp.route('/<int:id>/toggle')
@login_required
def toggle(id):
    c = Cliente.query.get_or_404(id)
    c.estado = not c.estado
    db.session.commit()
    flash(f'Cliente {"activado" if c.estado else "desactivado"}.', 'success')
    return redirect(url_for('clientes.lista'))


@clientes_bp.route('/buscar')
@login_required
def buscar():
    """Búsqueda AJAX para autocompletado"""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    clientes = Cliente.query.filter(
        db.or_(
            Cliente.codigo.ilike(f'%{q}%'),
            Cliente.nombre.ilike(f'%{q}%')
        )
    ).filter_by(estado=True).limit(10).all()
    return jsonify([{
        'id': c.id,
        'codigo': c.codigo,
        'nombre': c.nombre,
        'tiene_tarifa': c.tarifas.count() > 0
    } for c in clientes])
