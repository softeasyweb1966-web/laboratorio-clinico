from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import ListaPrecio, ListaPrecioItem, Cups
from app.listas_precios import listas_bp


# ── LISTA DE LISTAS ───────────────────────────────────────────────────────────

@listas_bp.route('/')
@login_required
def lista():
    q = request.args.get('q', '').strip()
    query = ListaPrecio.query
    if q:
        query = query.filter(
            db.or_(
                ListaPrecio.codigo.ilike(f'%{q}%'),
                ListaPrecio.nombre.ilike(f'%{q}%')
            )
        )
    listas = query.order_by(ListaPrecio.nombre).all()
    return render_template('listas_precios/lista.html', listas=listas, q=q)


# ── NUEVA LISTA ───────────────────────────────────────────────────────────────

@listas_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def nueva():
    if request.method == 'POST':
        codigo = request.form.get('codigo', '').strip().upper()
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()

        if not codigo or not nombre:
            flash('Código y nombre son obligatorios.', 'danger')
        elif ListaPrecio.query.filter_by(codigo=codigo).first():
            flash(f'Ya existe una lista con el código {codigo}.', 'danger')
        else:
            lp = ListaPrecio(codigo=codigo, nombre=nombre,
                             descripcion=descripcion, estado=True)
            db.session.add(lp)
            db.session.commit()
            flash(f'Lista "{nombre}" creada. Ahora agrega los servicios.', 'success')
            return redirect(url_for('listas.editar_items', id=lp.id))

    return render_template('listas_precios/form.html', lista=None)


# ── EDITAR ENCABEZADO ─────────────────────────────────────────────────────────

@listas_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    lp = ListaPrecio.query.get_or_404(id)
    if request.method == 'POST':
        lp.nombre = request.form.get('nombre', '').strip()
        lp.descripcion = request.form.get('descripcion', '').strip()
        lp.estado = request.form.get('estado') == 'on'
        db.session.commit()
        flash('Lista actualizada.', 'success')
        return redirect(url_for('listas.lista'))
    return render_template('listas_precios/form.html', lista=lp)


# ── CRUD DE ÍTEMS (servicios + valores) ───────────────────────────────────────

@listas_bp.route('/<int:id>/items', methods=['GET', 'POST'])
@login_required
def editar_items(id):
    lp = ListaPrecio.query.get_or_404(id)
    q = request.args.get('q', '').strip()

    # Filtrar ítems actuales
    items_query = ListaPrecioItem.query.filter_by(lista_id=id).join(Cups)
    if q:
        items_query = items_query.filter(
            db.or_(
                Cups.codigo.ilike(f'%{q}%'),
                Cups.descripcion.ilike(f'%{q}%')
            )
        )
    items = items_query.order_by(Cups.descripcion).all()

    return render_template('listas_precios/items.html', lista=lp, items=items, q=q)


@listas_bp.route('/<int:id>/items/agregar', methods=['POST'])
@login_required
def item_agregar(id):
    lp = ListaPrecio.query.get_or_404(id)
    cups_codigo = request.form.get('cups_codigo', '').strip().upper()
    valor_str = request.form.get('valor', '0').strip()

    cups = Cups.query.get(cups_codigo)
    if not cups:
        flash(f'CUPS {cups_codigo} no existe.', 'danger')
        return redirect(url_for('listas.editar_items', id=id))

    try:
        valor = float(valor_str)
    except ValueError:
        flash('Valor inválido.', 'danger')
        return redirect(url_for('listas.editar_items', id=id))

    existente = ListaPrecioItem.query.filter_by(
        lista_id=id, cups_codigo=cups_codigo).first()
    if existente:
        existente.valor = valor
        flash(f'Valor del CUPS {cups_codigo} actualizado.', 'success')
    else:
        item = ListaPrecioItem(lista_id=id, cups_codigo=cups_codigo, valor=valor)
        db.session.add(item)
        flash(f'CUPS {cups_codigo} agregado a la lista.', 'success')

    db.session.commit()
    return redirect(url_for('listas.editar_items', id=id))


@listas_bp.route('/<int:id>/items/<int:item_id>/valor', methods=['POST'])
@login_required
def item_actualizar_valor(id, item_id):
    """Actualización inline del valor desde la tabla."""
    item = ListaPrecioItem.query.get_or_404(item_id)
    try:
        item.valor = float(request.form.get('valor', 0))
        db.session.commit()
        return jsonify({'ok': True, 'valor': float(item.valor)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@listas_bp.route('/<int:id>/items/<int:item_id>/eliminar', methods=['POST'])
@login_required
def item_eliminar(id, item_id):
    item = ListaPrecioItem.query.get_or_404(item_id)
    cups_cod = item.cups_codigo
    db.session.delete(item)
    db.session.commit()
    flash(f'CUPS {cups_cod} eliminado de la lista.', 'success')
    return redirect(url_for('listas.editar_items', id=id))


@listas_bp.route('/<int:id>/toggle')
@login_required
def toggle(id):
    lp = ListaPrecio.query.get_or_404(id)
    lp.estado = not lp.estado
    db.session.commit()
    flash(f'Lista {"activada" if lp.estado else "desactivada"}.', 'success')
    return redirect(url_for('listas.lista'))


# ── API AJAX ──────────────────────────────────────────────────────────────────

@listas_bp.route('/api/buscar')
@login_required
def api_buscar():
    """Para el selector de lista en el formulario de clientes."""
    q = request.args.get('q', '').strip()
    listas = ListaPrecio.query.filter(
        db.or_(
            ListaPrecio.codigo.ilike(f'%{q}%'),
            ListaPrecio.nombre.ilike(f'%{q}%')
        )
    ).filter_by(estado=True).order_by(ListaPrecio.nombre).limit(15).all()
    return jsonify([{
        'id': lp.id,
        'codigo': lp.codigo,
        'nombre': lp.nombre,
        'total_items': lp.items.count()
    } for lp in listas])


@listas_bp.route('/api/<int:id>/cups')
@login_required
def api_cups_lista(id):
    """Retorna los CUPS de una lista para usar en atenciones."""
    items = ListaPrecioItem.query.filter_by(lista_id=id).join(Cups).filter(
        Cups.estado == True
    ).order_by(Cups.descripcion).all()
    return jsonify([{
        'codigo': i.cups_codigo,
        'descripcion': i.cups.descripcion,
        'valor': float(i.valor),
        'es_transporte': i.cups.es_transporte
    } for i in items])
