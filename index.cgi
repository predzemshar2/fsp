#!/usr/bin/env python3

import sys
from wsgiref.handlers import CGIHandler

sys.path.insert(0, '/home/v/vyachesl83/.local/lib/python3.10/site-packages')
sys.path.insert(0, '/home/v/vyachesl83/h2/public_html') 
from app import create_app as _create_app # <— Обратите внимание на подчёркивание!

def application(environ, start_response):
    app = _create_app()

    with app.app_context():
        return app(environ, start_response)

CGIHandler().run(application)
