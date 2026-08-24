from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app import db
from app.models import Usuario
from app.auth import auth_bp


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        usuario = Usuario.query.filter_by(username=username).first()

        if usuario and usuario.check_password(password):
            if not usuario.activo:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'danger')
                return render_template('auth/login.html')

            login_user(usuario, remember=remember)
            usuario.ultimo_acceso = datetime.utcnow()
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/cambiar-password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    if request.method == 'POST':
        password_actual = request.form.get('password_actual', '')
        password_nueva = request.form.get('password_nueva', '')
        password_confirma = request.form.get('password_confirma', '')

        if not current_user.check_password(password_actual):
            flash('La contraseña actual es incorrecta.', 'danger')
        elif password_nueva != password_confirma:
            flash('Las contraseñas nuevas no coinciden.', 'danger')
        elif len(password_nueva) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
        else:
            current_user.set_password(password_nueva)
            db.session.commit()
            flash('Contraseña actualizada correctamente.', 'success')
            return redirect(url_for('main.index'))

    return render_template('auth/cambiar_password.html')
