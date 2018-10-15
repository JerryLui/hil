# NOT USED AT ALL
import os
from flask import Flask

# API
def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        'DEVICE_HOST'='',
        'DEVICE_PORT'=5005,
        'DEVICE_LOG_DRIVE'=r'C:\Users\JerryL\Downloads\Archives',
        'DEVICE_SW_DRIVE'=r'C:\Users\JerryL\Downloads\Archives\Software',
        'CREATE_ADMIN'=True,
        'ADMIN_CREDENTIALS'={'password': 'admin123'},
        'CREATE_DIRECTORIES'=True,
        'SQLALCHEMY_DATABASE_URI'='sqlite:///static/db/database.db',
        'SQLALCHEMY_TRACK_MODIFICATIONS'=False,
        'PROJECT_FOLDER'=os.path.dirname(os.path.abspath(__file__)),
        'UPLOAD_FOLDER'=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp', 'uploads')
    )





