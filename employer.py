from flask import Blueprint, render_template, redirect, url_for, flash, request, g, jsonify,session
from forms import CreateJobForm,EditEmployerProfileForm
from models import User, Job, CandidateProfile, Invitation,EmployerProfile
# CandidateJobMatch, 
from extensions import db
import json
from sqlalchemy import func



from datetime import datetime,timedelta

employer_bp = Blueprint('employer', __name__, template_folder='templates')

@employer_bp.route('/create-job', methods=['GET','POST'])
def create_job():
    form = CreateJobForm()
    if form.validate_on_submit():
        new_job = Job(
            user_id=g.user.id,  # ⚡️ Используем ID пользователя
            title=form.title.data,
            specialization=form.specialization.data,
            tech_stack=form.tech_stack.data.replace(',', ', ').strip(),
            grade=form.grade.data
        )
        
        db.session.add(new_job)
        db.session.commit()

        flash(f"Вакансия '{new_job.title}' успешно опубликована.", "success")
        return redirect(url_for('employer.dashboard'))
    return render_template('employer/create_job.html', title='Новая вакансия', form=form)

@employer_bp.route('/dashboard', methods=['GET'])
def dashboard():
    if not g.user or g.user.role != 'employer':
        return redirect(url_for('employer.job_dashboard'))

    profile = getattr(g.user, "profile", None)
    # jobs = profile.job_listings if profile and hasattr(profile, "job_listings") else []
    jobs = Job.query.filter_by(user_id=g.user.id).all()
    enriched_jobs = []
    for job in jobs:
        
        job_stack_words = [w.strip().lower() for w in (job.tech_stack or '').split(',') if w.strip()]

        candidates_q = (
            CandidateProfile.query
            .filter(CandidateProfile.specialization == job.specialization)
            .order_by(CandidateProfile.total_score.desc())
            .limit(30)
        )
        candidates = candidates_q.all()

        candidates_data = []
        for c in candidates:
            candidate_stack_words = [w.strip().lower() for w in (c.tech_stack or '').split(',') if w.strip()]
            stack_match = bool(set(job_stack_words) & set(candidate_stack_words))
            # stack_match = True
            if stack_match:
                candidates_data.append({
                    "profile_id": c.id,
                    "full_name": c.full_name if c.full_name else None,
                    "desired_salary": c.desired_salary if c.desired_salary else None,
                    "tech_stack": c.tech_stack if c.tech_stack else None,
                    "grade": c.grade if c.grade else None,
                    "fsp_achievements": c.fsp_achievements if c.fsp_achievements else None,
                    "evaluation_score": c.evaluation_score if c.evaluation_score else None,
                    "fsp_achievements_confirmed": c.fsp_achievements_confirmed if c.fsp_achievements_confirmed else None,
                    
                    # "employer_invitation_id": c.employer_invitation_id if c.employer_invitation_id else None,
                    
                    "employer_invitation_id": next(
                        (inv.id for inv in c.invitations 
                        if inv.sender_user_id == g.user.id), 
                        None
                    ),
                    "total_score": c.total_score if c.total_score else None,
                    "stack_match": stack_match,
                })

        grade_display = job.grade.capitalize() if job.grade else "Не указан"

        enriched_jobs.append({
            "obj": job,
            "grade_display": grade_display,
            "candidates": candidates_data,
            "cand": candidates_q.count(),
        })



    return render_template(
        'employer/dashboard.html',
        title='Панель управления',
        user_id=g.user.id,
        company_name=getattr(profile, "company_name", ""),
        description=getattr(profile, "description", ""),
        job_count=len(enriched_jobs),
        jobs_with_candidates=enriched_jobs,
      
        
    )

    
@employer_bp.route('/edit-profile-e', methods=['GET','POST'])
def edit_profile_e():
    """Редактирование профиля работодателя."""
    
    if not g.user or g.user.role != 'employer':
        
        return redirect(url_for('employer.job_dashboard'))

    profile = getattr(g.user, "profile", None)  # Используем универсальное свойство .profile

    #  Если профиля ещё нет, создаём пустой объект формы
    form = EditEmployerProfileForm(obj=profile or {})

    if request.method == 'POST' and form.validate_on_submit():
        # Создаём или обновляем профиль
        if profile is None:
            profile = EmployerProfile(user_id=g.user.id)
        
        profile.company_name = form.company_name.data.strip()[:255]
        profile.description = form.description.data.strip()
        profile.contact_email = form.contact_email.data.strip()[:255] or None

        db.session.add(profile)
        db.session.commit()

        flash("Ваш профиль успешно обновлён!", "success")
        return redirect(url_for('employer.dashboard'))

    return render_template(
        'employer/edit_profile.html',
        title='Редактировать профиль компании',
        form=form,
        user_id=g.user.id
    )

@employer_bp.route('/employer/invite', methods=['POST'])
def invite_candidate():
    # 1. Проверка роли
    if g.user.role != 'employer':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('employer.dashboard'))

    # 2. Получение данных из формы
    job_id = request.form.get('job_id', type=int)
    candidate_profile_id = request.form.get('candidate_profile_id', type=int)
    salary_offer = request.form.get('salary_offer', type=int) or None
    message_text = request.form.get('message_text', default='Приглашаем вас на собеседование!')

    if not job_id :
        flash('Некорректные данные job_id', 'error')
        return redirect(request.referrer or url_for('employer.dashboard'))
    if not candidate_profile_id:
        flash('Некорректные данные candidate_profile_id', 'error')
        return redirect(request.referrer or url_for('employer.dashboard'))

    # 3. Проверка: вакансия принадлежит текущему работодателю
    job = Job.query.filter_by(id=job_id, user_id=g.user.id).first()
    if not job:
        flash('Эта вакансия вам не принадлежит', 'error')
        return redirect(request.referrer or url_for('employer.dashboard'))

    # 4. Проверка: кандидат существует
    candidate = CandidateProfile.query.get(candidate_profile_id)
    if not candidate:
        flash('Кандидат не найден', 'error')
        return redirect(request.referrer or url_for('employer.dashboard'))

    # 5. Создаем приглашение
    invitation = Invitation(
        sender_user_id=g.user.id,
        recipient_candidate_id=candidate.id,
        message_text=message_text,
        salary_offer=salary_offer,
        status='sent'
    )

    # try:
    db.session.add(invitation)

    db.session.flush()  # чтобы получить invitation.id до commit
    invitation_id = invitation.id

    # 2. Обновляем профиль кандидата
    candidate_profile = CandidateProfile.query.get(candidate.id)
    if not candidate_profile:
        db.session.rollback()
        return jsonify({'error': 'Профиль кандидата не найден'}), 404

    candidate_profile.invitation_received_at = datetime.utcnow()
    candidate_profile.employer_invitation_id = invitation_id

    # 3. Финальный коммит
    try:
        db.session.commit()
        # return jsonify({            'success': True,            'invitation_id': invitation_id,            'candidate_profile_id': andidate.id
        # }), 200
        flash(f'Приглашение для {candidate.full_name} отправлено!', 'success')
    except IntegrityError:
        db.session.rollback()
        # return jsonify({'error': 'Ошибка целостности данных'}), 400
        flash('Ошибка при сохранении приглашения', 'error')

    # db.session.commit()
# except Exception as e:
    # db.session.rollback()
    #

    return redirect(request.referrer or url_for('employer.dashboard'))
@employer_bp.route('/employer/candidate/<int:candidate_id>', methods=['GET'])
def view_candidate_profile(candidate_id):
    if g.user.role != 'employer':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('employer.dashboard'))

    candidate = CandidateProfile.query.get_or_404(candidate_id)
    
    
    return render_template(
        'employer/view_candidate_profile.html',
        candidate=candidate,
        title=f'Профиль кандидата: {candidate.full_name}'
    )
