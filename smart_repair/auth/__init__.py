from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_user, logout_user, login_required

from smart_repair.extensions import db
from smart_repair.forms import LoginForm, RegisterForm, ActionForm
from smart_repair.models import User, UserRole, Role, CustomerProfile

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.is_active and not user.archived_at and user.check_password(form.password.data):
            login_user(user, remember=False, fresh=True)
            flash("Welcome back. Your workspace is ready.", "success")
            return redirect(url_for("main.dashboard"))
        form.password.errors.append("Email or password is incorrect, or this account is inactive.")
    return render_template("auth.html", form=form, register=False, title="Welcome back")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        phone = form.phone.data.strip() or None
        if User.query.filter_by(email=email).first():
            form.email.errors.append("This email is already registered.")
        elif phone and User.query.filter_by(phone=phone).first():
            form.phone.errors.append("This phone number is already registered.")
        else:
            role = Role.query.filter_by(name="Customer").first()
            if not role:
                flash("Please run the database seed command before registering.", "error")
                return redirect(url_for("auth.register"))
            user = User(full_name=form.full_name.data.strip(), email=email, phone=phone)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            db.session.add_all([CustomerProfile(user_id=user.id), UserRole(user_id=user.id, role_id=role.id)])
            db.session.commit()
            login_user(user)
            flash("Account created. Start by registering your first device.", "success")
            return redirect(url_for("customer.devices"))
    return render_template("auth.html", form=form, register=True, title="Create your account")


@bp.post("/logout")
@login_required
def logout():
    if ActionForm().validate_on_submit():
        logout_user()
        from flask import session
        session.clear()
    return redirect(url_for("auth.login"))
