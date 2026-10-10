# Описание проекта
Система управления вакансиями и кандидатами на базе Flask с интеграцией SQLAlchemy и MySQL, а также c системой автоматического тестирования и оценивания кандидатов.

# Требования к окружению
Python версии: 3.10
База данных: MySQL
Веб-сервер: Apache/mod_cgi

# Установка и развертывание
1. Клонирование репозитория

git clone <ссылка_на_репозиторий>
cd проект

2. Создание виртуального окружения

python3.10 -m venv venv
source venv/bin/activate  

для Windows: venv\\Scripts\\activate

Установка зависимостей

Создайте файл requirements.txt:
Flask==2.3.2
Flask-SQLAlchemy==2.5.1
Flask-Login==0.6.2
PyMySQL==1.0.2
SQLAlchemy==2.0.54
Werkzeug==3.1.9
WTForms==3.2.2
pydantic==2.13.5
pydantic-settings==2.15.0
PyJWT==2.3.0
redis==3.5.3
requests==2.25.1

# Установите зависимости:

pip install -r requirements.txt

# Настройка базы данных
Создайте базу данных MySQL
Обновите конфигурационные файлы config.py (впишите пользователя, пароль, имя_базы)

# Запуск проекта
Настройте переменные окружения (файл .inv)
Запустите приложение:
flask run

# Структура проекта

проект/
├── app.py
├── models.py
├── config.py
├── auth.py
├── candidates.py
├──  employer.py
├── extensions.py
├── forms.py
├── templates/
│   └── ...
└── static/
    └── ...

# Конфигурация для продакшена
Настройте Apache/mod_cgi
Обновите права доступа
Проверьте все зависимости

# Полезные команды
Миграции базы данных:

flask db init
flask db migrate
flask db upgrade

Проверьте совместимость версий библиотек
Настройте параметры подключения к базе данных
Установите права доступа к файлам проекта
