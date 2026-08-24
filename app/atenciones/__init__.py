from flask import Blueprint

atenciones_bp = Blueprint('atenciones', __name__, template_folder='templates')

from app.atenciones import routes  # noqa
