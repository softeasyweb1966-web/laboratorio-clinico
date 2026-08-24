from flask import Blueprint

listas_bp = Blueprint('listas', __name__)

from app.listas_precios import routes  # noqa
