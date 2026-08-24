from flask import Blueprint

cartera_bp = Blueprint('cartera', __name__, template_folder='templates')

from app.cartera import routes  # noqa
