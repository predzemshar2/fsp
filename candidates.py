# candidates.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, g, jsonify,session
from models import CandidateProfile,User , AdditionalSpecialization , Invitation
import ast
from forms import EditCandidateProfileForm
from extensions import db
import json
from datetime import datetime,timedelta


candidate_bp = Blueprint('candidate', __name__, template_folder='templates')

@candidate_bp.route('/profile')
def profile():
    if not g.user or g.user.role != 'candidate':
        return jsonify({
            'error': 'Access denied',
            'session_raw': str(dict(session)),
            'g_user': bool(g.user),
            'user_role': getattr(g.user, 'role', None)
        }), 403

    # ⚡️ Используйте явное получение профиля через внешний ключ
    candidate = CandidateProfile.query.filter_by(user_id=g.user.id).first()
    form = EditCandidateProfileForm(obj=candidate)
    
    invitations = candidate.invitations.filter(
        Invitation.status != 'declined'
    ).order_by(
        Invitation.id.desc()
    ).all()

    return render_template(
        'candidates/profile.html',
        title='Мой профиль кандидата',
        candidate=candidate,
        form=form,
        user_id=g.user.id,
        invitations=invitations
    )

# @candidate_bp.route('/profile_more')
@candidate_bp.route('/profile_more/<int:candidate_id>')
def profile_more(candidate_id):
    """Страница подробной оценки теста."""
    # or g.user.role != 'candidate'
    if not g.user :
        abort(403) 

    # candidate = getattr(g.user, "profile", None)
    candidate = CandidateProfile.query.get_or_404(candidate_id)

    if not candidate or not candidate.evaluation_score:
        flash("Тест ещё не был оценён.", "info")
        return redirect(url_for('candidate.profile'))  

    try:
        questions = json.loads(candidate.issued_questions_json or '{}')
        answers = json.loads(candidate.user_answers_json or '{}')
        comments = json.loads(candidate.evaluator_comments_json or '{}')
        
        evaluation_data = []
        for q_num_str in sorted(questions.keys()):
            question_text = questions.get(q_num_str, "")

            q_num_int = int(q_num_str)

            answer_text = answers.get(q_num_str, "").strip()[:250]
            comment_obj = comments.get(q_num_str, {})

            score = comment_obj.get("score") or "-"
            feedback = comment_obj.get("comment") or ""

            # decoded_feedback = feedback.encode('latin1').decode('unicode_escape')
            decoded_feedback = feedback

            evaluation_data.append({
                "num": q_num_int,
                "question": question_text,
                "answer": answer_text,
                "score": score,
                "feedback": decoded_feedback
            })

    except json.JSONDecodeError as e:
        error_message = f"Ошибка парсинга JSON: {str(e)}"
        
        flash(error_message, "danger")
        return redirect(url_for('candidate.profile'))  

    except Exception as e:
        error_message = f"Произошла ошибка при обработке данных: {str(e)}"
        print(error_message)
        flash(error_message, "danger")
        return redirect(url_for('candidate.profile'))  
    return render_template(
        'candidates/profile_more.html',
        title='Подробная оценка теста',
        user_id=g.user.id,
        evaluation_data=evaluation_data,
        candidate_id=candidate_id, 
        total_score=candidate.evaluation_score+candidate.fsp_achievements_confirmed
    )
# @candidate_bp.route('/edit-profile', methods=['GET','POST']) # Для редактирования
# def edit_profile():
#     return render_template('candidates/edit_profile.html')



@candidate_bp.route('/edit-profile', methods=['GET','POST'])
def edit_profile():
    # ⚡️ Проверка авторизации должна быть первой!
    if not g.user or g.user.role != 'candidate':
        abort(403)
    candidate = getattr(g.user, "profile", None)  # Используем универсальное свойство .profile
    if candidate.evaluation_score >0:
        flash("Вы прошли уже подтверждение квалификации, профиль закрыт для редактирования", "warning")
        return redirect(url_for('candidate.profile'))

    # ⚡️ Критически важная проверка
    if not candidate:
        flash("У вас ещё нет заполненного профиля.", "warning")
        return redirect(url_for('candidate.profile'))

    form = EditCandidateProfileForm(obj=candidate)

    if request.method == 'POST' and form.validate_on_submit():
        # Сохраняем данные только если профиль существует
        candidate.full_name = form.full_name.data.strip()[:255]
        candidate.resume_text = form.resume_text.data.strip()
        
        # Новые поля
        candidate.specialization = form.specialization.data
        candidate.tech_stack = form.tech_stack.data.replace(',', ', ').strip()
        candidate.grade = form.grade.data

        candidate.fsp_id = form.fsp_id.data
        candidate.desired_salary = form.desired_salary.data
        candidate.fsp_achievements = form.fsp_achievements.data

        db.session.commit()
        flash("Ваш профиль успешно обновлён!", "success")
        return redirect(url_for('candidate.profile'))

    return render_template(
        'candidates/edit_profile.html',
        title='Редактирование профиля',
        form=form,
        user_id=g.user.id
    )

@candidate_bp.route('/start-test', methods=['GET','POST'])
def start_test():
    """Запускает новый тест или показывает подтверждение."""
    
    # Проверка авторизации и роли
    if not g.user or g.user.role != 'candidate':
        abort(403)
    candidate_profile = getattr(g.user, "profile", None)
    if not candidate_profile.specialization or not candidate_profile.tech_stack or not candidate_profile.grade:
        flash("Отредактируйте сначала профиль - укажите направление, стек и грейд!", "warning")
        return redirect(url_for('candidate.edit_profile'))
    # Если это GET-запрос — показываем кнопку подтверждения
    if request.method == 'GET':
        return render_template(
            'candidates/confirm_start.html',
            title='Подтвердить квалификацию'
        )

    # ⚡️ Безопасная проверка существования профиля
    

    if not candidate_profile:
        flash("Ваш профиль ещё не заполнен. Пожалуйста, обновите его.", "warning")
        return redirect(url_for('candidate.edit_profile'))

    # Генерируем вопросы только если специализация указана
    specialization = candidate_profile.specialization.strip()
    if not specialization:
        flash("Выберите направление IT в профиле.", "warning")
        return redirect(url_for('candidate.edit_profile'))
    tech_stack = candidate_profile.tech_stack.strip()
    if not tech_stack:
        flash("Выберите стек в профиле.", "warning")
        return redirect(url_for('candidate.edit_profile'))
    grade = candidate_profile.grade.strip()
    if not grade:
        flash("Выберите грейд в профиле.", "warning")
        return redirect(url_for('candidate.edit_profile'))

    try:
        questions_dict = generate_gigachat_questions(specialization,tech_stack,grade)
    except Exception as e:
        print(f"API ERROR: {e}")
        flash("Не удалось получить вопросы. Попробуйте позже.", "danger")
        return redirect(url_for('candidate.profile'))

    # Сохраняем метаданные
    candidate_profile.test_started_at = datetime.utcnow()
    candidate_profile.issued_questions_json = json.dumps(questions_dict)
    candidate_profile.user_answers_json = '{}'
    candidate_profile.evaluation_score = None
    db.session.commit()

    flash("Тест успешно запущен!", "success")
    return redirect(url_for('candidate.take_test'))  # Перенаправляем на вопросы
def generate_gigachat_questions(spec,tech_stack,grade,p=""):
    import requests
    import os
    import json
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole
    
    k=os.getenv('AUTH_KEY')
    # os.environ['GRPC_DEFAULT_SSL_ROOTS_FILE_PATH'] = 'combined_certs.crt'
    if p=="":
        prompt = 'Сгенерируй 10 технических вопросов для кандидата '+grade+' уровня по направлению '+spec+' и стеку технологий '+tech_stack+', на которые можно ответить одним-двумя предложениями. Например: Объясните смысл функции из стека, объсните пример кода, как работает такая-то технология/механизм, какие отличия и преимущества между такими-то технологиями, и т.п. Вопросы должны быть разной сложности. Ответы не нужны. Формат json {1:"Вопрос...", 2:"Вопрос...",3:...}'
    else:
        prompt = p
    client = GigaChat(
        base_url="https://api.giga.chat/v1",
        credentials=k,
        scope="GIGACHAT_API_PERS",
        verify_ssl_certs=False,
    )

    chat = Chat(
        model="GigaChat-3-Ultra",
        messages=[Messages(role=MessagesRole.USER, content=prompt)],
    )

    resp = client.chat(chat)

    choices_list = resp.choices
    message_dict = choices_list[0].message
    text = message_dict.content
    text = text.replace("json\n{\n","{\n").replace("```","")
    json_data = json.loads(text)
    # print(json_data)
    return json_data

def prepare_gigachat_prompt(profile):
    """Генерирует текстовый запрос для нейросети."""
    
    # Загружаем вопросы и ответы из базы
    questions = json.loads(profile.issued_questions_json or '{}')
    answers = json.loads(profile.user_answers_json or '{}')

    # Формируем список пар "Вопрос - Ответ"
    evaluation_pairs = []
    for q_num_str, question_text in sorted(questions.items()):
        answer_text = answers.get(q_num_str, '').strip()
        
        # Если ответа нет, ставим ноль баллов сразу
        if not answer_text:
            evaluation_pairs.append(f"{q_num_str}: 0 баллов (нет ответа)")
            continue
            
        # Для корректного парсинга удаляем лишние символы
        clean_answer = answer_text.replace('"', "'") #.replace("\n", "<br>")
        pair = f'{q_num_str}. Вопрос: "{question_text}". Ответ: "{clean_answer}" \n'
        evaluation_pairs.append(pair)

    # Собираем финальный промт
    prompt = f'Вы оцениваете технические ответы кандидата на позицию {profile.grade} ' + f'(направление: {profile.specialization}, стек технологий: {profile.tech_stack}).\n\n' + 'Максимум за каждый вопрос можно поставить до 10 баллов.\n'+'Если ответа нет, поставьте 0 баллов. Учтите, что кандидату требовалось отвечать одним-двумя предложениями.\n'+'Комментарий должен быть кратким (до двух предложений). Ответ должен быть проанализирован в рамках насколько верно описана технология, ответил ли кандидат на весь вопрос, легко ли понять ответ без дополнительных пояснений? Ответы, лишенные смылса , по типу Correct answer - оценить в ноль баллов.\n'+'Не пишите вступлений или заключений. Если подозреваете, что  ответ скопирован из интернета - занизьте оценку, добавьте соответствующее замечание в комментарий.\n'+'\n'.join(evaluation_pairs) + '\n\n'+'Ответьте строго в формате JSON:\n'+'{"Общая суммарная оценка":<число>, "1":"<баллы> Комментарий...", "2":"..."}'
    

    return prompt
@candidate_bp.route('/evaluate-test', methods=['GET'])
def evaluate_test():
    """Запускает процесс автоматической оценки ответов."""
    if not g.user or g.user.role != 'candidate':
        abort(403)

    profile = getattr(g.user, "profile", None)
    if not profile or not profile.test_started_at:
        flash("Тест ещё не запущен.", "warning")
        return redirect(url_for('candidate.profile'))

    # try:
        # # Генерируем промт для нейросети
        # prompt = prepare_gigachat_prompt(profile)
        # # console.log(prompt)
        # # ⚡️ Вызов API GigaChat
        # response = requests.post(
        #     url="https://api.giga.chat/v1/chat/completions",
        #     headers={
        #         "Authorization": f"Bearer {os.getenv('GIGACHAT_API_KEY')}",
        #         "Content-Type": "application/json"
        #     },
        #     verify=False,
        #     json={
        #         "model": "gpt-3.5-turbo",
        #         "messages": [{"role": "user", "content": prompt}]
        #     }
        # )

        # if response.status_code != 200:
        #     raise Exception(f"GigaChat error [{response.status_code}]: {response.text}")

        # data = response.json()
        # result = data["choices"][0]["message"]["content"]

        # Парсим результат как JSON
    try:
        # eval_result = json.loads(result.strip())
        eval_result = generate_gigachat_questions("","","",prepare_gigachat_prompt(profile))
    except json.JSONDecodeError as e:
        print(f"JSON ERROR: {e}\nRAW RESPONSE: {eval_result[:200]}...")
        flash("Нейросеть вернула некорректный формат ответа. Попробуйте позже.", "danger")
        return redirect(url_for('candidate.profile'))

    # Сохраняем данные в базу
    total_score = int(eval_result.get("Общая суммарная оценка") or 0)
    comments = {}

    for key, val in eval_result.items():
        if key.isdigit():  # Это номер вопроса
            parts = val.split(maxsplit=1)
            score = int(parts[0].split()[0]) if len(parts) > 0 else 0
            comment = parts[1].strip() if len(parts) > 1 else ""
            comments[key] = {"score": score, "comment": comment}

    # Обновляем профиль
    db.session.add(profile)
    profile.evaluation_score = total_score
    profile.total_score=profile.evaluation_score+profile.fsp_achievements_confirmed
    profile.evaluator_comments_json = json.dumps(comments)

    # Блокируем редактирование профиля на месяц при успешной оценке
    if total_score >= 50:
        profile.last_edit_block_until = datetime.utcnow() + timedelta(days=30)

    db.session.commit()

    flash(f"Тест успешно оценен! Общая оценка: {total_score}/100.", "success")

    # except Exception as e:
    #     print(str(e))
    #     flash("Ошибка при отправке запроса к оценке." + prompt, "danger")

    return redirect(url_for('candidate.profile'))    
@candidate_bp.route('/downgrade-grade', methods=['POST','PUT'])
def downgrade_grade():
    """Позволяет кандидату понизить грейд после неудачной оценки."""
    if not g.user or g.user.role != 'candidate':
        abort(403)

    current_grade = g.user.profile.grade.name.lower()
    grades_order = ['junior', 'middle', 'senior']

    # Находим индекс текущего грейда
    idx = grades_order.index(current_grade)
    if idx == 0:
        flash("Это минимальный грейд. Вы не можете его понизить.", "info")
        return redirect(url_for('candidate.profile'))

    new_grade_name = grades_order[idx - 1]
    g.user.profile.grade = new_grade_name  # SQLAlchemy Enum

    # Сбрасываем все метаданные теста
    g.user.profile.test_started_at = None
    g.user.profile.issued_questions_json = ''
    g.user.profile.user_answers_json = ''
    g.user.profile.evaluation_score = None
    g.user.profile.evaluator_comments_json = ''

    db.session.commit()

    flash(f"Ваш грейд снижен до {new_grade_name.capitalize()}. Пожалуйста, пройдите новый тест.", "success")
    return redirect(url_for('candidate.edit_profile'))
@candidate_bp.route('/take-test')
def take_test():
    """Страница с вопросами."""
    
    # Проверка авторизации и роли
    if not g.user or g.user.role != 'candidate':
        abort(403)

    candidate_profile = getattr(g.user, "profile", None)

    # Если профиль не существует или тест не начат
    if not candidate_profile or not candidate_profile.test_started_at:
        flash("Тест ещё не был запущен. Пожалуйста, нажмите кнопку 'Приступить' на странице профиля.", "warning")
        return redirect(url_for('candidate.profile'))

    # Загружаем вопросы из базы данных
    try:
        questions = json.loads(candidate_profile.issued_questions_json)
        answers = json.loads(candidate_profile.user_answers_json)
    except Exception as e:
        print(f"JSON ERROR: {e}")
        flash("Не удалось загрузить вопросы. Попробуйте запустить тест заново.", "danger")
        return redirect(url_for('candidate.start_test'))

    # Проверяем наличие хотя бы одного вопроса
    if len(questions) == 0:
        flash("Вопросы для теста отсутствуют. Обратитесь к администратору.", "warning")
        return redirect(url_for('candidate.profile'))

    return render_template(
        'candidates/take_test.html',
        title='Технический тест',
        questions=questions,
        answers=answers
    )

@candidate_bp.route('/save-test-answer/<int:q_num>', methods=['POST'])
def save_answer(q_num):
    """AJAX-обработчик сохранения ответа на вопрос."""
    
    # ⚡️ Проверка авторизации и профиля
    if not g.user or not getattr(g.user.profile, "test_started_at", None):
        return jsonify({'status': 'error', 'message': 'Тест не запущен'}), 403
    # time_limit = timedelta(minutes=20) 
    # elapsed_time = datetime.utcnow() - g.user.profile.test_started_at 
    # if elapsed_time > time_limit: 
    #     flash("Время для прохождения теста закончилось.", "warning") 
    #     return jsonify({'status': 'expired'})

    answer_text = request.form.get('answer')

    try:
        current_answers = json.loads(g.user.profile.user_answers_json)
    except Exception as e:
        print(f"JSON ERROR: {e}")
        return jsonify({'status': 'error', 'message': f'Не удалось загрузить ответы ({str(e)})'}), 500

    # Сохраняем ответ
    current_answers[str(q_num)] = answer_text.strip()[:500]

    # ⚡️ Защита от SQLAlchemy DetachedInstanceError
    # Убедимся, что объект сессии привязан к текущему запросу
    db.session.add(g.user.profile)  
    g.user.profile.user_answers_json = json.dumps(current_answers)

    try:
        db.session.commit()
    except Exception as e:
        print(f"DATABASE ERROR: {e}")
        return jsonify({'status': 'error', 'message': f'Ошибка базы данных ({str(e)})'}), 500

    return jsonify({'status': 'ok'})
@candidate_bp.route('/confirm-fsp', methods=['POST'])
def confirm_fsp():
    """Подтверждение достижений ФСП."""
    
    if not g.user or g.user.role != 'candidate':
        abort(403)

    # Проверяем наличие ID участника
    fsp_id = getattr(g.user.profile, "fsp_id", None)
    if not fsp_id:
        flash("Вы не указали свой ID участника ФСП.", "warning")
        return redirect(url_for('candidate.edit_profile'))

    # ⚡️ Подтверждаем достижения
    g.user.profile.fsp_achievements_confirmed = 5
    g.user.profile.fsp_confirmation_date = datetime.utcnow()

    # Блокируем редактирование профиля на месяц
    g.user.profile.last_edit_block_until = datetime.utcnow() + timedelta(days=30)

    # Рассчитываем новую общую оценку: текущая оценка теста + 5 за ФСП
    current_score = getattr(g.user.profile, "evaluation_score", 0) or 0
    # new_total_score = min(current_score + 5, 100)  # Не более 100
    new_total_score = current_score + g.user.profile.fsp_achievements_confirmed

    g.user.profile.total_score = new_total_score  # Сохраняем итоговую оценку

    db.session.commit()

    flash(f"Поздравляем! Ваши достижения ФСП подтверждены. Ваша общая оценка повышена до {new_total_score} / 100.", "success")
    return redirect(url_for('candidate.profile'))
@candidate_bp.route('/add-specialization', methods=['POST'])
def add_specialization():
    new_spec = request.form.get('specialization').strip().lower()
    if len(new_spec) > 2 and new_spec != g.user.candidate.specialization:
        spec_obj = AdditionalSpecialization(specialization_name=new_spec)
        g.user.candidate.additional_specializations.append(spec_obj)
        db.session.commit()
        flash(f"Специализация '{new_spec}' добавлена!", "success")
    return redirect(url_for('candidate.profile'))
@candidate_bp.route('/add-additional-spec', methods=['POST'])
def add_additional_spec():
    # ⚡️ Создаём форму здесь!
    form = EditCandidateProfileForm()
    
    if not g.user or g.user.role != 'candidate':
        abort(403)

    candidate = getattr(g.user, "profile", None)

    selected_value = request.form.get("new_specialization")

    # Теперь мы можем безопасно обращаться к choices через связанный экземпляр
    existing_specs = [spec.specialization_name.lower() for spec in candidate.additional_specializations]
    
    # Получаем метки из связанного поля формы
    valid_choices = {key: label for key, label in form.specialization.choices}

    if selected_value and len(selected_value.strip()) > 2:
        new_spec_key = selected_value.lower().replace(' ', '_')
        
        # Проверяем, существует ли такой ключ в списке выбора
        if new_spec_key in valid_choices:
            new_spec_name = valid_choices[new_spec_key].capitalize()
            
            if new_spec_key not in existing_specs:
                spec_obj = AdditionalSpecialization(
                    candidate_profile_id=candidate.id,
                    specialization_name=new_spec_name[:50]
                )
                
                db.session.add(spec_obj)
                db.session.commit()

                flash(f"Специализация '{selected_value}' успешно добавлена!", "success")
                return redirect(url_for('candidate.profile'))
            else:
                flash(f"Специализация '{selected_value}' уже существует.", "info")
        else:
            flash("Выбранное направление отсутствует в списке допустимых значений.", "warning")
    elif not selected_value:
        flash("Пожалуйста, выберите действительное направление.", "warning")
    else:
        flash("Название направления слишком короткое или некорректно.", "warning")

    return redirect(url_for('candidate.profile'))