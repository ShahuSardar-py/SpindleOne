from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.extensions import db
from app.auth.models import User

bp = Blueprint('auth', __name__, url_prefix='/auth')

def seed_demo_users():
    """Seeds default demo users if they do not exist."""
    demo_users = [
        {"username": "admin", "role": "SuperAdmin", "password": "admin123"},
        {"username": "keeper", "role": "store keeper", "password": "keeper123"},
        {"username": "hr_user", "role": "HR", "password": "hr123"},
        {"username": "accountant", "role": "accounts", "password": "acct123"}
    ]
    try:
        for du in demo_users:
            user = User.query.filter_by(username=du["username"]).first()
            if not user:
                new_user = User(username=du["username"], role=du["role"])
                new_user.set_password(du["password"])
                db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding demo users: {e}")

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', '').strip()

        user = User.query.filter_by(username=username).first()
        if user:
            pw_match = user.check_password(password)
            print(f"[AUTH] User '{username}' found. Registered Role: '{user.role}'. Selected Role: '{role}'. Password Match: {pw_match}")
            if pw_match:
                if user.role != role:
                    flash(f"Access Denied: Selected role does not match user's registered clearance.", "error")
                    return render_template('auth/login.html')
                
                session.clear()
                session['user_id'] = user.user_id
                session['username'] = user.username
                session['role'] = user.role
                flash(f"Operator authenticated. Clearance level: {user.role}", "success")
                return redirect(url_for('main.home'))
            else:
                print(f"[AUTH] Password check failed for user '{username}'.")
                flash("Invalid credentials.", "error")
                return render_template('auth/login.html')
        else:
            print(f"[AUTH] User '{username}' NOT found in database.")
            flash("Invalid credentials.", "error")
            return render_template('auth/login.html')
            
    return render_template('auth/login.html')

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', '').strip()

        if not username or not password or not role:
            flash("All fields are required.", "error")
            return render_template('auth/signup.html')

        if role not in ['SuperAdmin', 'store keeper', 'HR', 'accounts']:
            flash("Invalid role selected.", "error")
            return render_template('auth/signup.html')

        existing = User.query.filter_by(username=username).first()
        if existing:
            flash("Username already exists.", "error")
            return render_template('auth/signup.html')

        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html')

@bp.route('/logout')
def logout():
    session.clear()
    flash("Session terminated.", "info")
    return redirect(url_for('auth.login'))
