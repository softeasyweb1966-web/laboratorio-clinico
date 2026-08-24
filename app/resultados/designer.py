import json
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify,
)
from flask_login import login_required
from app.models import Exam, LayoutCell, Parameter
from app import db

designer_bp = Blueprint('designer', __name__)


@designer_bp.route('/<int:exam_id>')
@login_required
def design(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    params = exam.parameters.filter_by(active=True).order_by(Parameter.order_index).all()
    cells = (
        exam.layout_cells
        .filter(LayoutCell.row >= 0)
        .order_by(LayoutCell.row, LayoutCell.col)
        .all()
    )
    metadata = exam.layout_cells.filter_by(row=-1, col=-1, cell_type='meta').first()
    cells_data = [_cell_to_dict(c) for c in cells]
    return render_template(
        'exams/designer.html',
        exam=exam,
        params=params,
        cells_json=json.dumps(cells_data),
        layout_settings_json=json.dumps(_layout_settings(metadata)),
    )


@designer_bp.route('/<int:exam_id>/save', methods=['POST'])
@login_required
def save_layout(exam_id):
    """
    Receive JSON array of cell definitions and persist them.
    Each cell: {row, col, rowspan, colspan, cell_type, content, parameter_id, style}
    """
    exam = Exam.query.get_or_404(exam_id)
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify({'ok': False, 'error': 'Invalid payload'}), 400

    result_cells_without_parameter = [
        cell_data
        for cell_data in data
        if cell_data.get('cell_type') == 'result' and not cell_data.get('parameter_id')
    ]
    if result_cells_without_parameter:
        return jsonify({
            'ok': False,
            'error': 'Cada celda de resultado debe estar asociada a un parámetro.'
        }), 400

    # Delete all existing cells for this exam
    LayoutCell.query.filter_by(exam_id=exam_id).delete()
    db.session.flush()

    metadata = next(
        (cell_data for cell_data in data if cell_data.get('cell_type') == 'meta'),
        None,
    )
    if metadata:
        db.session.add(LayoutCell(
            exam_id=exam_id,
            row=-1,
            col=-1,
            cell_type='meta',
            content=metadata.get('content', '{}'),
            style='{}',
        ))

    for cell_data in data:
        # Skip metadata rows (col widths, etc.)
        if int(cell_data.get('row', 0)) < 0:
            continue
        cell = LayoutCell(exam_id=exam_id)
        cell.row = int(cell_data.get('row', 0))
        cell.col = int(cell_data.get('col', 0))
        cell.rowspan = int(cell_data.get('rowspan', 1))
        cell.colspan = int(cell_data.get('colspan', 1))
        cell.cell_type = cell_data.get('cell_type', 'label')
        cell.content = cell_data.get('content', '')
        pid = cell_data.get('parameter_id')
        cell.parameter_id = int(pid) if pid else None
        style = cell_data.get('style')
        cell.style = json.dumps(style) if isinstance(style, dict) else (style or '{}')
        db.session.add(cell)

    db.session.commit()
    return jsonify({'ok': True})


@designer_bp.route('/<int:exam_id>/preview')
@login_required
def preview(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    cells = exam.layout_cells.filter(LayoutCell.row >= 0).order_by(LayoutCell.row, LayoutCell.col).all()
    grid = _cells_to_grid(cells)
    return render_template('exams/preview.html', exam=exam, grid=grid)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _layout_settings(metadata):
    if not metadata or not metadata.content:
        return {}
    try:
        settings = json.loads(metadata.content)
    except (TypeError, ValueError):
        return {}
    return settings if isinstance(settings, dict) else {'colWidths': settings}

def _cell_to_dict(cell):
    return {
        'id': cell.id,
        'row': cell.row,
        'col': cell.col,
        'rowspan': cell.rowspan,
        'colspan': cell.colspan,
        'cell_type': cell.cell_type,
        'content': cell.content or '',
        'parameter_id': cell.parameter_id,
        'style': cell.style_dict,
        'parameter_name': cell.parameter.name if cell.parameter else None,
    }


def _cells_to_grid(cells):
    """
    Converts flat list of LayoutCell into a 2D list suitable for rendering
    an HTML table.  Returns list of rows; each row is a list of cells
    (or None where a previous colspan/rowspan covers the position).
    """
    if not cells:
        return []

    max_row = max(c.row + c.rowspan - 1 for c in cells)
    max_col = max(c.col + c.colspan - 1 for c in cells)

    grid = [[None] * (max_col + 1) for _ in range(max_row + 1)]
    occupied = set()

    sorted_cells = sorted(cells, key=lambda c: (c.row, c.col))
    result_rows = []

    for cell in sorted_cells:
        # Mark occupied positions
        for r in range(cell.row, cell.row + cell.rowspan):
            for cc in range(cell.col, cell.col + cell.colspan):
                occupied.add((r, cc))
        grid[cell.row][cell.col] = cell

    rows = []
    for r in range(max_row + 1):
        row_cells = []
        for c in range(max_col + 1):
            cell = grid[r][c]
            if cell is not None:
                row_cells.append(cell)
            elif (r, c) not in occupied:
                # empty cell placeholder
                row_cells.append({'empty': True, 'row': r, 'col': c})
        if row_cells:
            rows.append(row_cells)

    return rows
