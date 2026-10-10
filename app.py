import os
import sys
from dotenv import load_dotenv
from flask import Flask, jsonify, session, g, request, redirect, url_for
import ast


load_dotenv()
sys.path.insert(0, '/home/v/vyachesl83/.local/lib/python3.10/site-packages')
# НЕ ДЕЛАЙТЕ ЭТО ЗДЕСЬ!
# from models import db, User, CandidateProfile

from extensions import db

def create_app():
    app = Flask(__name__)
    
    # from wtforms.csrf.core import CSRF               иконки⚠️⚡️📌
    # @app.context_processor 
    # def inject_wtf_macros(): 
    #     return dict(wtf=CSRF._get_renderer(app))

    # #### Регистрация blueprint-аутентификации ####
    from auth import auth_bp
    from candidates import candidate_bp
    from employer import employer_bp

    
    # app.register_blueprint(auth_bp, url_prefix='/auth')
    # app.register_blueprint(candidate_bp)

    # # Конфигурация БД
    # app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    # # ... остальные настройки
    app.register_blueprint(auth_bp, url_prefix='/auth') # ⚡️ Регистрируем новые маршруты кандидата без префикса 
    app.register_blueprint(candidate_bp)
    app.register_blueprint(employer_bp)

    # Конфигурация БД
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['SESSION_COOKIE_SECURE'] = True  
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' 

   
    from models import db, User, CandidateProfile 

    db.init_app(app)

    @app.before_request
    def load_logged_in_user():
        raw_session = dict(session)
        try:
            user_id = int(raw_session.get('user_id'))
            if not user_id and '_id' in raw_session:
                user_data = ast.literal_eval(raw_session['_id'])
                user_id = int(user_data.get('user_id'))
            
            # Теперь это должно работать, потому что db уже инициализировано!
            g.user = User.query.filter_by(id=user_id).first()
        except Exception as e:
            # print(f"SESSION ERROR !!: {e}")
            g.user = None


    @app.route('/')
    def index():
        if not g.user:
            return redirect(url_for('auth.login'))

        return jsonify({'status': 'ok', 'message': 'Hackathon API is running'})

    ### Этап 2: Создание профиля кандидата ###

    @app.route('/1')

    def get_access_token():
        import base64
        from requests import post as http_post
        from config import CLIENT_ID, SECRET # Или os.getenv('...')
        auth_string = f"{CLIENT_ID}:{SECRET}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        response = http_post(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth/token",
            data={
                "grant_type": "client_credentials",  # Обязательный параметр!
                "scope": "GIGACHAT_API_PERS"         # Ваш scope
            },
            headers={
                "Authorization": f"Basic {encoded_auth}",  # Вот так должно быть!
                "Accept": "application/json"
            },
            verify=False  
        )

        if not response.ok:
            raise Exception(f"GigaChat error [{response.status_code}]: {response.text}")

        return response.json()["access_token"]
    # @app.route('/candidate/profile', methods=['GET','POST'])
    # def create_candidate_profile():
    #     # Отладочный вывод
    #     if request.args.get('debug'):
    #         return jsonify({
    #             'session_raw': str(dict(session)),
    #             'g_user': bool(g.user),
    #             'user_role': getattr(g.user, 'role', None)
    #         })

    #     if not g.user or g.user.role != 'candidate':
    #         return jsonify({'error': 'Access denied!!!'}), 403

    #     data = request.json
    #     if not data:
    #         return jsonify({'error': 'No JSON provided'}), 400

    #     profile = CandidateProfile.query.filter_by(user_id=g.user.id).first()

    #     if not profile:
    #         profile = CandidateProfile(user_id=g.user.id)
    #         db.session.add(profile)


    #     profile.full_name = data.get('full_name', '')
    #     profile.resume_text = data.get('resume_text', '')
        
    #     salary_str = data.get('desired_salary')
    #     try:
    #         profile.desired_salary = int(salary_str) if salary_str is not None else None
    #     except ValueError:
    #         return jsonify({'error': 'Salary must be an integer'}), 400

    #     db.session.commit()
    #     return jsonify({'message': 'Profile updated', 'id': profile.id}), 200

    @app.route('/send-invite', methods=['POST'])
    def send_invite():
        data = request.json
        recipient_id = int(data['recipient_id'])
        message_text = data['message_text']
        salary_offer = int(data['salary_offer']) if data['salary_offer'] else None

        # Проверяем права доступа
        if not g.user or g.user.role != 'employer':
            # abort(403)
            return jsonify({'error': 'Ваша роль не подходит'}), 404

        # Находим профиль кандидата
        candidate = CandidateProfile.query.get(recipient_id)
        if not candidate:
            return jsonify({'error': 'Кандидат не найден'}), 404

        # Создаем приглашение
        invite = Invitation(
            sender_user_id=g.user.id,
            recipient_candidate_id=recipient_id,
            message_text=message_text[:1000],
            salary_offer=salary_offer
        )
        db.session.add(invite)
        db.session.commit()

        
        existing_invites_json = json.loads(candidate.received_invitations_json or '{}')
        existing_invites_json[str(g.user.id)] = {
            "company": getattr(g.user.employer_profile, "company_name", ""),
            "date": datetime.utcnow().isoformat(),
            "status": "new"
        }
        candidate.received_invitations_json = json.dumps(existing_invites_json)
        db.session.commit()



        return jsonify({"status": "ok"})
    @app.route('/invitation/accept/<int:invitation_id>')
    def accept_invitation(invitation_id):
        invitation = Invitation.query.get_or_404(invitation_id)
        if invitation.status == 'sent':
            invitation.status = 'accepted'
            db.session.commit()
            flash('Приглашение принято')
        return redirect(url_for('candidate_profile', candidate_id=invitation.recipient_candidate_id))

    @app.route('/invitation/decline/<int:invitation_id>')
    def decline_invitation(invitation_id):
        invitation = Invitation.query.get_or_404(invitation_id)
        if invitation.status == 'sent':
            invitation.status = 'declined'
            db.session.commit()
            flash('Приглашение отклонено')
        return redirect(url_for('candidate_profile', candidate_id=invitation.recipient_candidate_id))

    return app

# Для запуска через gunicorn локально или WSGI
app = create_app()


