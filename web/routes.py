from flask import Flask, render_template, request, send_from_directory, flash, get_flashed_messages, redirect
from multiprocessing import Pipe, Process
from werkzeug.utils import secure_filename
from werkzeug.contrib.fixers import ProxyFix
from flask_sqlalchemy import SQLAlchemy
import time
import random
import os
import sys

from models import Task, File, User, Status

# Flask app config
app = Flask(__name__)
app.debug = True
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///static/db/database.db'
app.config['LOG_INDEX'] = dict()  # dict
app.config['TASK_LIST'] = dict()  # dict
app.config['PROJECT_FOLDER'] = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['PROJECT_FOLDER'], 'tmp')
app.config['LOG_DRIVE'] = r'C:\Users\JerryL\Downloads\Archives'
db = SQLAlchemy(app)

@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    return render_template('index.html', tasks=Task.query_all(), logs=app.config['LOG_INDEX'].keys())


@app.route('/create', methods=['POST'])
def create_task():
    try:
        file = File.query.filter_by(file_name=request.form['filename']).first()
        db.session.add(Task(file_name=file.file_name, status=0))
        flash('Task created successfully', 'info')
        return index()
    except Exception as xcpt:
        return xcpt


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static/img', 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/upload', methods=['POST', 'GET'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return index()

        file = request.files['file']
        if file.filename == '':
            flash('No select file')
            return index()
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER']))
            return index()
    elif request.method == 'GET':
        return render_template('upload.html')


# DB File update
def update_db_file():
    [db.session.add(File(file_name=log.name, file_path=log.path)) for log in _recursive_log_scan()]
    db.session.commit()


def _recursive_log_scan():
    """ Iterator of all files ending with dvl in log_drive """
    for entry in os.scandir(app.config['LOG_DRIVE']):
        if entry.is_dir(follow_symlinks=False):
            yield from _recursive_log_scan(entry)
        elif os.path.splitext(entry)[1] == '.dvl':
            yield entry


class FakeProcess(Process):
    def __init__(self, log, pipe_conn):
        self.log = log
        self.pipe_conn = pipe_conn
        super().__init__()

    def run(self):
        self.pipe_conn.send(1)
        time.sleep(random.randint(5, 10))

        self.pipe_conn.send(2)
        time.sleep(random.randint(7, 13))

        if random.randint(0, 3):
            self.pipe_conn.send(-1)
        else:
            self.pipe_conn.send(0)
        return


if __name__ == '__main__':
    update_db_file()
    app.run()
    # app.run(host='10.239.125.56')
