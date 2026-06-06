from flask import Blueprint

bp = Blueprint('zarvec', __name__, url_prefix='/zarvec')

from . import routes
