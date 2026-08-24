from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app import db
from app.models import Cups
from app.cups import cups_bp


@cups_bp.route('/')
@login_required
def lista():
    q = request.args.get('q', '').strip()
    query = Cups.query
    if q:
        query = query.filter(
            db.or_(
                Cups.codigo.ilike(f'%{q}%'),
                Cups.descripcion.ilike(f'%{q}%')
            )
        )
    cups = query.order_by(Cups.codigo).limit(500).all()
    return render_template('cups/lista.html', cups=cups, q=q)


@cups_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    return _form_cups(None)


@cups_bp.route('/<codigo>/editar', methods=['GET', 'POST'])
@login_required
def editar(codigo):
    c = Cups.query.get_or_404(codigo)
    return _form_cups(c)


def _form_cups(cups):
    if request.method == 'POST':
        codigo = request.form.get('codigo', '').strip().upper()
        descripcion = request.form.get('descripcion', '').strip()
        valor_str = request.form.get('valor', '0').strip()
        es_transporte = request.form.get('es_transporte') == 'on'
        estado = request.form.get('estado') == 'on'

        try:
            valor = float(valor_str)
        except ValueError:
            valor = 0

        if not codigo or not descripcion:
            flash('Código y descripción son obligatorios.', 'danger')
        else:
            if cups is None:
                if Cups.query.get(codigo):
                    flash(f'Ya existe un CUPS con código {codigo}.', 'danger')
                    return render_template('cups/form.html', cups=None)
                c = Cups(codigo=codigo, descripcion=descripcion, valor=valor,
                         es_transporte=es_transporte, estado=estado)
                db.session.add(c)
                flash('CUPS creado correctamente.', 'success')
            else:
                cups.descripcion = descripcion
                cups.valor = valor
                cups.es_transporte = es_transporte
                cups.estado = estado
                flash('CUPS actualizado correctamente.', 'success')

            db.session.commit()
            return redirect(url_for('cups.lista'))

    return render_template('cups/form.html', cups=cups)


@cups_bp.route('/<codigo>/toggle')
@login_required
def toggle(codigo):
    c = Cups.query.get_or_404(codigo)
    c.estado = not c.estado
    db.session.commit()
    flash(f'CUPS {"activado" if c.estado else "desactivado"}.', 'success')
    return redirect(url_for('cups.lista'))


@cups_bp.route('/buscar')
@login_required
def buscar():
    """Búsqueda AJAX de CUPS"""
    q = request.args.get('q', '').strip()
    cliente_id = request.args.get('cliente_id')
    if len(q) < 2:
        return jsonify([])

    if cliente_id:
        # Buscar en la lista de precios del cliente
        from app.models import Cliente, ListaPrecioItem
        cliente = Cliente.query.get(int(cliente_id))

        if cliente and cliente.lista_precio_id:
            # Cliente con lista de precios asignada: mostrar solo esos CUPS
            items = ListaPrecioItem.query.filter_by(lista_id=cliente.lista_precio_id).join(Cups).filter(
                Cups.estado == True,
                db.or_(Cups.codigo.ilike(f'%{q}%'), Cups.descripcion.ilike(f'%{q}%'))
            ).order_by(Cups.descripcion).limit(50).all()
            return jsonify([{
                'codigo': i.cups_codigo,
                'descripcion': i.cups.descripcion,
                'valor': float(i.valor),
                'es_transporte': i.cups.es_transporte
            } for i in items])

    # Sin cliente o cliente sin lista: buscar en todos los CUPS activos
    cups_list = Cups.query.filter(
        db.or_(Cups.codigo.ilike(f'%{q}%'), Cups.descripcion.ilike(f'%{q}%'))
    ).filter_by(estado=True).order_by(Cups.descripcion).limit(50).all()
    return jsonify([{
        'codigo': c.codigo, 'descripcion': c.descripcion,
        'valor': float(c.valor), 'es_transporte': c.es_transporte
    } for c in cups_list])
