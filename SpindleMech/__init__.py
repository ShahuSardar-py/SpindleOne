from flask import Blueprint

bp = Blueprint(
    'spindlemech',
    __name__,
    url_prefix='/mech',
    template_folder='mechtemplates'
)

from . import routes