from flask import Blueprint

pacientes_bp = Blueprint('pacientes', __name__, template_folder='templates')

from app.pacientes import routes  # noqa
