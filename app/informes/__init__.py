from flask import Blueprint

informes_bp = Blueprint('informes', __name__, template_folder='templates')

from app.informes import routes  # noqa
