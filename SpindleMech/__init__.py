from flask import Blueprint

bp = Blueprint(
    'spindlemech',
    __name__,
    url_prefix='/mech',
    template_folder='templates'
)

from . import routes