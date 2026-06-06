from flask import render_template, request, redirect, url_for, session, flash
from app.zarvec.lock_manager import get_lock_state, set_lock_state
from . import bp

@bp.route('/', methods=['GET'])
def index():
    if session.get('zarvec_authorized'):
        state = get_lock_state()
        return render_template('zarvec/dashboard.html', state=state)
    return render_template('zarvec/login.html')

@bp.route('/login', methods=['POST'])
def login():
    passcode = request.form.get('passcode', '').strip()
    state = get_lock_state()
    
    if passcode == state.get('passcode'):
        session['zarvec_authorized'] = True
        flash("Authorization successful. Access granted.", "success")
        return redirect(url_for('zarvec.index'))
    else:
        flash("Invalid access key. Authentication failed.", "error")
        return render_template('zarvec/login.html')

@bp.route('/logout', methods=['GET'])
def logout():
    session.pop('zarvec_authorized', None)
    flash("Administrative session terminated.", "info")
    return redirect(url_for('zarvec.index'))

@bp.route('/save', methods=['POST'])
def save():
    if not session.get('zarvec_authorized'):
        flash("Unauthorized action.", "error")
        return redirect(url_for('zarvec.index'))
    
    is_locked = 'is_locked' in request.form
    lock_reason = request.form.get('lock_reason', '').strip()
    new_passcode = request.form.get('new_passcode', '').strip()
    
    if not lock_reason:
        lock_reason = "Access temporarily suspended due to outstanding payment. Please contact system administrator."
        
    set_lock_state(
        is_locked=is_locked,
        lock_reason=lock_reason,
        passcode=new_passcode if new_passcode else None
    )
    
    flash("System lock state updated successfully.", "success")
    return redirect(url_for('zarvec.index'))
