from flask import Blueprint

cups_bp = Blueprint('cups', __name__, template_folder='templates')

from app.cups import routes  # noqa
