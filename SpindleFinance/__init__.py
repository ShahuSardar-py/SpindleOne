from flask import Blueprint

bp = Blueprint(
    'spindlefinance',
    __name__,
    url_prefix='/finance',
    template_folder='templates'
)

from . import routes