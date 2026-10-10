from flask import Blueprint, request, jsonify, session, g
from models import db, User, CandidateProfile, EmployerProfile # Импортируем из models.py!
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm
from flask import render_template, flash, redirect, url_for

auth_bp = Blueprint('auth', __name__)

############
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email

# Создаём новую форму
class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    role = SelectField('Роль',
                       choices=[
                           ('candidate', 'Кандидат'),
                           ('employer', 'Работодатель')
                       ],
                       validators=[DataRequired()]
                      )
    submit = SubmitField('Зарегистрироваться')

@auth_bp.route('/register', methods=['GET','POST'])
def register():
    # Для GET-запроса рендерим форму
    if request.method == 'GET':
        form = RegistrationForm()
        return render_template('register.html', title='Регистрация', form=form)

    # Для POST-запроса сохраняем данные
    form = RegistrationForm()
    if not form.validate_on_submit():
        flash("Пожалуйста, заполните все поля.", "danger")
        return render_template('register.html', title='Регистрация', form=form)

    existing_user = User.query.filter_by(email=form.email.data).first()
    if existing_user:
        flash("Пользователь с таким email уже существует.", "warning")
        return redirect(url_for('auth.register'))

    user = User(
        email=form.email.data,
        role=form.role.data
    )
    user.set_password(form.password.data)

    db.session.add(user)
    db.session.flush()

    profile_model = CandidateProfile if user.role == 'candidate' else EmployerProfile
    profile = profile_model(user_id=user.id)
    db.session.add(profile)
    db.session.commit()

    flash(f"Пользователь {user.email} успешно зарегистрирован!", "success")
    return redirect(url_for('auth.login')) # Перенаправляем на вход
##########
# @auth_bp.route('/register', methods=['POST'])
# def register():
#     data = request.json
#     if not data or not data.get('email'):
#         return jsonify({'error': 'Missing data'}), 400

#     existing_user = User.query.filter_by(email=data['email']).first()
#     if existing_user:
#         return jsonify({'error': 'Email already exists'}), 409

#     # Создаём пользователя
#     user = User(
#         email=data['email'],
#         role=data.get('role', 'candidate')
#     )
#     user.set_password(data['password'])  # Хешируем пароль

#     # Предварительно фиксируем сессию, чтобы получить ID пользователя
#     # На Timeweb это критично при работе через CGI.
#     db.session.add(user)
#     db.session.flush() # <-- ВНИМАНИЕ! СБРОС БЕЗ КОМИТА

#     # Теперь создаём профиль
#     profile_model = CandidateProfile if user.role == 'candidate' else EmployerProfile
#     profile = profile_model(user_id=user.id)
#     db.session.add(profile)
#     db.session.commit() # Только здесь коммитим ВСЁ вместе

#     return jsonify({
#         'message': 'User created',
#         'user_id': user.id,
#         'profile_id': profile.id
#     }), 201

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(email=form.email.data).first()
#         if user and user.check_password(form.password.data):
#             session['user_id'] = user.id
#             session['_id'] = {'user_id': user.id, 'role': user.role}

#             # return jsonify({'message': 'Logged in', 'role': user.role}), 200
#             next_page = request.args.get('next') # Для защиты CSRF 
#             return redirect(next_page or url_for('candidate.profile'))
#         else:
#             flash("Неверные учетные данные", "danger")
#             return redirect(url_for('auth.login'))
#             # return jsonify({'error': 'Invalid credentials'}), 401

#     
#     return render_template('login.html', title='Вход', form=form)
# # ...
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            session['_id'] = {'user_id': user.id, 'role': user.role}
            
            next_page = request.args.get('next')
            
            if user.role == 'candidate':
                return redirect(next_page or url_for('candidate.profile'))
            elif user.role == 'employer':
                return redirect(next_page or url_for('employer.dashboard'))  
            else:
                flash("Неизвестная роль.", "danger")
                return redirect(url_for('auth.login'))
    return render_template('login.html', title='Вход', form=form)
@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
# jsonify({'message': 'Logged out'}), 200