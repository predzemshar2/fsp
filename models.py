from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship 
from extensions import db  # <— Импортируем из вашего единого расширения!

class User(db.Model):
    """Пользователь — общая таблица для кандидатов и работодателей."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.Enum('candidate', 'employer'), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    #  Универсальный доступ через одно свойство
    @property
    def profile(self):

        if self.role == 'candidate':
            return self.candidate_profile
        elif self.role == 'employer':
            return self.employer_profile
        return None
    @property 
    def jobs(self): 
        if self.role == 'employer': 
            return getattr(self, "job_listings", []) 
        else: 
            return []
    # ⚡️ Обратные связи должны быть уникальными по имени бэкпопулейтс
    candidate_profile = db.relationship(
        "CandidateProfile",
        uselist=False,
        back_populates="user",          # Назовём просто user
        cascade="all, delete-orphan"
    )

    employer_profile = db.relationship(
        "EmployerProfile",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan"
    )

#  Профили с простым внешним ключом user_id.
class CandidateProfile(db.Model):  
    """Профиль кандидата: резюме, зарплата, достижения."""
    __tablename__ = 'candidate_profile'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # ⚡️ Убираем лишние прямые отношения owner_user!
    # Оставляем только одну связь обратно к пользователю
    user = db.relationship("User", back_populates="candidate_profile")

    full_name = db.Column(db.String(255))
    resume_text = db.Column(db.Text)
    desired_salary = db.Column(db.Integer)
    fsp_id = db.Column(db.String(100)) # ID в Федерации спортивного программирования

    specialization = db.Column(db.String(50))  # Направление IT
    tech_stack = db.Column(db.Text)            # Стек технологий через запятую или JSON
    grade = db.Column(db.Enum('junior', 'middle', 'senior','lead'))  
    fsp_achievements = db.Column(db.Text)      # Достижения ФСП (текстовое поле)

    # Подтверждение квалификации через тест
    test_started_at = db.Column(db.DateTime)          # Когда запущен тест
    issued_questions_json = db.Column(db.Text)        # JSON со списком вопросов {1:"Вопрос..."}
    user_answers_json = db.Column(db.Text)            # JSON с ответами {"1": "Мой ответ"}
    evaluation_score = db.Column(db.Integer,default=0)         # Оценка от 0 до 100
    evaluator_comments_json = db.Column(db.Text)     # JSON с комментариями [{"question_id": 3, "comment": "..."}]

    # Достижения ФСП и подтверждение
    fsp_achievements_confirmed = db.Column(db.Integer, default=0)  # оценка достижений
    fsp_confirmation_date = db.Column(db.DateTime)                     # Дата подтверждения

    # Данные о приглашении (на будущее)
    invitation_received_at = db.Column(db.DateTime)
    employer_invitation_id = db.Column(db.String(50))
    contact_email = db.Column(db.String(255))  # Контакт работодателя

    total_score = db.Column(db.Integer,default=0)
    
    # Дополнительные квалификации (многократная связь)
    additional_specializations = relationship(
        'AdditionalSpecialization',
        backref='candidate_profile',
        cascade="all, delete-orphan"
    )
    invitations = db.relationship(
        'Invitation', 
        backref='candidate', 
        foreign_keys='Invitation.recipient_candidate_id',
        lazy='dynamic'  # для возможности фильтрации
    )
    invitation_received_at = db.Column(db.DateTime)
    employer_invitation_id = db.Column(db.Integer)
class EmployerProfile(db.Model): 
    """Профиль работодателя: название компании, описание."""
    __tablename__ = 'employer_profile'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    company_name = db.Column(db.String(255))
    description = db.Column(db.Text)

    
    user = db.relationship("User", back_populates="employer_profile")

class AdditionalSpecialization(db.Model):
    __tablename__ = 'additional_specializations'
    
    # ⚡️ Добавляем автоинкрементный id
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    candidate_profile_id = db.Column(
        db.Integer,
        db.ForeignKey('candidate_profile.id'),
        nullable=False
    )
    specialization_name = db.Column(db.String(50), nullable=False)


class Job(db.Model):
    """Вакансия работодателя."""
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # ID работодателя
    
    title = db.Column(db.String(255))          
    specialization = db.Column(db.String(50))
    tech_stack = db.Column(db.Text)
    grade = db.Column(db.Enum('junior', 'middle', 'senior'))

    employer = db.relationship(
        "User",
        backref=db.backref("job_listings", cascade="all, delete-orphan"),
        foreign_keys=[user_id]
    )



# class CandidateJobMatch(db.Model):  # Таблица связей
#     __tablename__ = 'candidate_job_matches'
#     job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), primary_key=True)
    
#     candidate_profile_id = db.Column(db.Integer, db.ForeignKey('candidate_profile.id'), primary_key=True)

#     relevance_score = db.Column(db.Float, default=0.0)  # Релевантность от 0 до 1

class Invitation(db.Model):
    """Приглашение кандидата на собеседование."""
    __tablename__ = 'invitations'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Работодатель
    recipient_candidate_id = db.Column(db.Integer, db.ForeignKey('candidate_profile.id'))
    
    message_text = db.Column(db.Text)
    salary_offer = db.Column(db.Integer)
    status = db.Column(db.Enum('sent', 'viewed', 'accepted', 'declined'), default='sent')