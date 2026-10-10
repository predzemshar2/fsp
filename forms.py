from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class EditCandidateProfileForm(FlaskForm):
    full_name = StringField("ФИО", validators=[DataRequired()])
    resume_text = TextAreaField("Резюме")
    desired_salary = StringField("Желаемая зарплата (₽)", validators=[
        Length(max=6, message="Зарплата слишком большая!")
    ])

    # Новые поля
    specialization = SelectField(
        "Направление",
        choices=[
            ('robotics', 'Робототехника'),
            ('webdev', 'Веб-разработка'),
            ('gamedev', 'GameDev'),
            ('ml', 'Machine Learning / AI'),
            ('data_science', 'Data Science'),
            ('cybersecurity', 'Кибербезопасность'),
            ('devops', 'DevOps'),
            ('mobile_development', 'Мобильная разработка'),
            ('iot', 'Интернет вещей (IoT)'),
            ('blockchian', 'Блокчейн-технологии'),
            ('virtual_reality', 'Виртуальная и дополненная реальность'),
            ('sap', 'SAP/1C/ERP'),
            ('asc', 'АСУ ТП')
        ],
        validators=[DataRequired()]
    )

    tech_stack = StringField(
        "Стек технологий (через запятую)",
        description="Пример: Python, Django, PostgreSQL"
    )

    grade = SelectField(
        "Грейд",
        choices=[
            ('junior', 'Junior'),
            ('middle', 'Middle'),
            ('senior', 'Senior'),
            ('lead', 'TeamLead')
        ],
        validators=[DataRequired()]
    )

    fsp_id = StringField("ID участника ФСП")  # Поле для будущего подтверждения
    fsp_achievements = StringField("Достижения участника ФСП")  # Поле для будущего подтверждения
    submit = SubmitField("Сохранить профиль")


class CreateJobForm(FlaskForm):
    title = StringField("Название вакансии", validators=[DataRequired()])
    # form = EditCandidateProfileForm()
    # choices1 = {key: label for key, label in form.specialization.choices}
    specialization = SelectField(
        "Направление",
        choices=[
            ('robotics', 'Робототехника'),
            ('webdev', 'Веб-разработка'),
            ('gamedev', 'GameDev'),
            ('ml', 'Machine Learning / AI'),
            ('data_science', 'Data Science'),
            ('cybersecurity', 'Кибербезопасность'),
            ('devops', 'DevOps'),
            ('mobile_development', 'Мобильная разработка'),
            ('iot', 'Интернет вещей (IoT)'),
            ('blockchian', 'Блокчейн-технологии'),
            ('virtual_reality', 'Виртуальная и дополненная реальность'),
            ('sap', 'SAP/1C/ERP'),
            ('asc', 'АСУ ТП')
        ],
        validators=[DataRequired()]
    )

    tech_stack = TextAreaField(
        "Стек технологий",
        description="Перечислите технологии через запятую.",
        validators=[Length(max=500)]
    )

    grade = SelectField(
        "Грейд",
        choices=[
            ('junior', 'Junior'),
            ('middle', 'Middle'),
            ('senior', 'Senior')
        ],
        validators=[DataRequired()]
    )

    submit = SubmitField('Опубликовать вакансию')


class EditEmployerProfileForm(FlaskForm):
    company_name = StringField("Название компании", validators=[DataRequired()])
    
    description = TextAreaField(
        "Описание компании",
        description="Чем занимается ваша компания? Какие технологии используете?",
        validators=[
            Length(max=500, message="Максимальная длина — 500 символов")
        ]
    )

    contact_email = StringField(
        "Контактный email для кандидатов",
        validators=[
            # Вы можете добавить валидатор Email здесь
            Length(max=255)
        ],
        render_kw={"placeholder": "Необязательно"}
    )

    submit = SubmitField('Сохранить профиль')