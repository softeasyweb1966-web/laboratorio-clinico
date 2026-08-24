from flask import Blueprint

rips_bp = Blueprint('rips', __name__, template_folder='templates')

from app.rips import routes  # noqa
