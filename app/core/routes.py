from flask import Blueprint, render_template, request, redirect, url_for

bp = Blueprint('main', __name__)

@bp.route('/', methods=['GET'])
def index():
    return redirect(url_for('main.home'))

@bp.route('/home', methods=['GET'])
@bp.route('/home/', methods=['GET'])
def home():
    return render_template('home.html')
