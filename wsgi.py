# WSGI entry point for PythonAnywhere
from app import create_app

app = create_app()
application = app  # PythonAnywhere looks for 'application'
