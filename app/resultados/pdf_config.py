import os
import json
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, current_app,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import PDFConfig
from app import db

pdf_config_bp = Blueprint('pdf_config', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
PATIENT_INFO_FIELDS = {
    'name': 'Nombre del paciente',
    'document': 'Documento',
    'birth_date': 'Fecha de nacimiento',
    'age_gender': 'Edad y género',
    'order_consecutive': 'Consecutivo de orden',
    'order_date': 'Fecha de la orden',
    'physician': 'Médico remitente',
    'diagnosis': 'Diagnóstico',
    'page_number': 'Número de página',
}
DEFAULT_PATIENT_INFO_LAYOUT = json.dumps([
    [
        {'field': 'name', 'label': 'Nombre'},
        {'field': 'document', 'label': 'Documento'},
    ],
    [
        {'field': 'birth_date', 'label': 'Fecha de nacimiento'},
        {'field': 'age_gender', 'label': 'Edad / género'},
    ],
    [
        {'field': 'order_consecutive', 'label': 'Consecutivo'},
        {'field': 'order_date', 'label': 'Fecha de orden'},
    ],
], ensure_ascii=False, indent=2)


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@pdf_config_bp.route('/')
@login_required
def list_configs():
    configs = PDFConfig.query.filter_by(user_id=current_user.id).all()
    default_cfg = PDFConfig.query.filter_by(is_default=True).first()
    return render_template('pdf_config/list.html', configs=configs, default_cfg=default_cfg)


@pdf_config_bp.route('/new', methods=['GET', 'POST'])
@login_required
def config_new():
    if request.method == 'POST':
        try:
            cfg = _config_from_form(PDFConfig(user_id=current_user.id))
        except ValueError as error:
            flash(str(error), 'danger')
            return _render_form(None)
        cfg.logo_path = _handle_logo_upload(request, current_app.config['UPLOAD_FOLDER'])
        db.session.add(cfg)
        db.session.commit()
        flash('Configuración PDF creada.', 'success')
        return redirect(url_for('pdf_config.list_configs'))
    return _render_form(None)


@pdf_config_bp.route('/<int:cfg_id>/edit', methods=['GET', 'POST'])
@login_required
def config_edit(cfg_id):
    cfg = PDFConfig.query.get_or_404(cfg_id)
    if cfg.user_id != current_user.id and current_user.role != 'admin':
        flash('Acceso restringido.', 'danger')
        return redirect(url_for('pdf_config.list_configs'))
    if request.method == 'POST':
        try:
            _config_from_form(cfg)
        except ValueError as error:
            flash(str(error), 'danger')
            return _render_form(cfg)
        logo_path = _handle_logo_upload(request, current_app.config['UPLOAD_FOLDER'])
        if logo_path:
            cfg.logo_path = logo_path
        db.session.commit()
        flash('Configuración PDF actualizada.', 'success')
        return redirect(url_for('pdf_config.list_configs'))
    return _render_form(cfg)


@pdf_config_bp.route('/<int:cfg_id>/set-default', methods=['POST'])
@login_required
def set_default(cfg_id):
    # Remove existing default
    PDFConfig.query.filter_by(is_default=True).update({'is_default': False})
    cfg = PDFConfig.query.get_or_404(cfg_id)
    cfg.is_default = True
    db.session.commit()
    flash(f'"{cfg.name}" establecida como configuración predeterminada.', 'success')
    return redirect(url_for('pdf_config.list_configs'))


@pdf_config_bp.route('/<int:cfg_id>/delete', methods=['POST'])
@login_required
def config_delete(cfg_id):
    cfg = PDFConfig.query.get_or_404(cfg_id)
    db.session.delete(cfg)
    db.session.commit()
    flash('Configuración eliminada.', 'warning')
    return redirect(url_for('pdf_config.list_configs'))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config_from_form(cfg):
    cfg.name = request.form.get('name', 'Default').strip()
    cfg.logo_position = request.form.get('logo_position', 'header')
    cfg.logo_alignment = request.form.get('logo_alignment', 'left')
    cfg.page_number_style = request.form.get('page_number_style', 'none')
    cfg.institution_name = request.form.get('institution_name', '').strip()
    cfg.institution_address = request.form.get('institution_address', '').strip()
    cfg.institution_phone = request.form.get('institution_phone', '').strip()
    cfg.header_text = request.form.get('header_text', '').strip()
    cfg.footer_text = request.form.get('footer_text', '').strip()
    patient_info_layout = request.form.get('patient_info_layout', '').strip()
    cfg.patient_info_layout = _validate_patient_info_layout(patient_info_layout)
    cfg.page_size = request.form.get('page_size', 'A4')
    cfg.margin_top = float(request.form.get('margin_top', 20) or 20)
    cfg.margin_bottom = float(request.form.get('margin_bottom', 20) or 20)
    cfg.margin_left = float(request.form.get('margin_left', 20) or 20)
    cfg.margin_right = float(request.form.get('margin_right', 20) or 20)
    cfg.show_qr = bool(request.form.get('show_qr'))
    cfg.show_watermark = bool(request.form.get('show_watermark'))
    cfg.watermark_text = request.form.get('watermark_text', '').strip()
    return cfg


def _render_form(cfg):
    raw_layout = cfg.patient_info_layout if cfg and cfg.patient_info_layout else DEFAULT_PATIENT_INFO_LAYOUT
    try:
        layout = json.loads(raw_layout)
    except (TypeError, ValueError):
        layout = json.loads(DEFAULT_PATIENT_INFO_LAYOUT)
    for row in layout:
        for cell in row:
            cell.setdefault('width', round(100 / len(row), 2))
    return render_template(
        'pdf_config/form.html',
        cfg=cfg,
        patient_info_fields=PATIENT_INFO_FIELDS,
        patient_info_layout_json=json.dumps(layout, ensure_ascii=False),
    )


def _validate_patient_info_layout(raw_layout):
    if not raw_layout:
        return DEFAULT_PATIENT_INFO_LAYOUT
    try:
        layout = json.loads(raw_layout)
    except json.JSONDecodeError as error:
        raise ValueError('La distribución de datos del paciente debe tener JSON válido.') from error

    if not isinstance(layout, list) or not layout:
        raise ValueError('La distribución debe ser una lista de filas con una o más columnas.')
    for row in layout:
        if not isinstance(row, list) or not row:
            raise ValueError('Cada fila debe contener al menos una columna.')
        if len(row) > 4:
            raise ValueError('Cada fila puede tener máximo cuatro campos.')
        total_width = 0
        for cell in row:
            if not isinstance(cell, dict) or cell.get('field') not in PATIENT_INFO_FIELDS:
                raise ValueError('Cada celda debe indicar un campo válido de datos del paciente.')
            if 'label' in cell and not isinstance(cell['label'], str):
                raise ValueError('La etiqueta de cada celda debe ser texto.')
            try:
                width = float(cell.get('width', 100 / len(row)))
            except (TypeError, ValueError) as error:
                raise ValueError('El ancho de cada campo debe ser numérico.') from error
            if not 1 <= width <= 100:
                raise ValueError('El ancho de cada campo debe estar entre 1 y 100%.')
            cell['width'] = width
            total_width += width
        if total_width > 100.01:
            raise ValueError('La suma de anchos en cada fila no puede superar 100%.')
    return json.dumps(layout, ensure_ascii=False)


def _handle_logo_upload(req, upload_folder):
    file = req.files.get('logo_file')
    if file and file.filename and _allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(upload_folder, filename)
        file.save(save_path)
        return filename
    return None
