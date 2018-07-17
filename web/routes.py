from flask import Flask, render_template, request, send_from_directory, flash, redirect, session, url_for, get_flashed_messages
from multiprocessing import Pipe, Process
from werkzeug.utils import secure_filename
from werkzeug.contrib.fixers import ProxyFix

import time
import random
import os
import sys

# Package specific imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import db, Task, File, User, Status
from forms import TaskForm, RegisterForm, LoginForm

# -------------------- APPLICATION CONFIGURATION --------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///static/db/database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.wsgi_app = ProxyFix(app.wsgi_app)
app.secret_key = 'a3067a6f5bc2b743c88ef8'
app.config['PROJECT_FOLDER'] = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['PROJECT_FOLDER'], 'tmp')
app.config['LOG_DRIVE'] = r'C:\Users\JerryL\Downloads\Archives'
app.config['STATUS_CODE'] = {-1: 'Failed', 0: 'Waiting', 1: 'Running', 2: 'Finished'}

db.init_app(app)
app.app_context().push()


# -------------------- FLASK --------------------
@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    if session.get('user_name', 0):
        form = TaskForm(File.query.all())
        print('rednering form')
    else:
        form = (LoginForm(prefix='login'), RegisterForm(prefix='register'))
    return render_template('index.html', form=form, tasks=Task.query.all())


@app.route('/create', methods=['POST'])
def create_task():
    form = TaskForm(Task.query_all())

    if not form.validate():
        flash('Invalid options!', 'warning')
    else:
        try:
            user = db.session.query(User).filter_by(name=session['user_name']).first()
            file = db.session.query(File).filter_by(name=form.file_name.data).first()
            new_task = Task(status=1, file_id=file.id, user_id=user.id)
            db.session.add(new_task)
            db.session.commit()
            flash('Task created!', 'success')
        except Exception as xcpt:
            db.session.rollback()
            print(xcpt)
    return index()


@app.route('/register', methods=['POST'])
def create_user():
    form = RegisterForm()

    if not form.validate():
        flash('Invalid input.', 'warning')
    else:
        user = db_insert_or_get(User, name=form.user_name.data, password=form.user_password.data)
        db.session.commit()

        flash('User created successfully.', 'success')
        session['user_name'] = user.name

    return index()


@app.route('/login', methods=['POST'])
def create_login():
    form = LoginForm()

    if not form.validate():
        flash('Invalid input.', 'warning')
    else:
        user_name = form.user_name.data
        user_password = form.user_password.data

        user = db.session.query(User).filter_by(user_name=user_name).first()
        if user is not None and user.check_password(user_password):
            session['user_name'] = user_name
            flash('Login successful.', 'success')
        else:
            flash('Incorrect login credentials.', 'warning')
    return index()


@app.route('/logout')
def logout():
    session.pop('user_name', None)
    return index()


@app.route('/upload', methods=['POST', 'GET'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'warning')
            return index()

        file = request.files['file']
        if file.filename == '':
            flash('No select file', 'warning')
            return index()
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER']))
            return index()
    elif request.method == 'GET':
        return render_template('upload.html')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static/img', 'favicon.ico', mimetype='image/vnd.microsoft.icon')


# -------------------- DATABASE --------------------
def db_insert_or_get(model, defaults=None, **kwargs):
    """
    Gets or inserts model into db wether or not if it exists or not.
    :returns : (model, bool)
    """
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance, True
    else:
        kwargs.update(defaults or {})
        instance = model(**kwargs)
        db.session.add(instance)
        return instance, False


def _populate_table_file():
    [db_insert_or_get(File, name=log.name, path=log.path) for log in _recursive_log_scan()]
    db.session.commit()


def _recursive_log_scan(directory=app.config['LOG_DRIVE']):
    """ Iterator of all files ending with dvl in log_drive """
    for entry in os.scandir(directory):
        if entry.is_dir(follow_symlinks=False):
            yield from _recursive_log_scan(entry)
        elif os.path.splitext(entry)[1] == '.dvl':
            yield entry


# -------------------- DB FILE --------------------


# -------------------- TEST ENV --------------------
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


# -------------------- MAIN --------------------
if __name__ == '__main__':
    _populate_table_file()
    db.create_all()
    app.run(debug=True)
    # app.run(host='10.239.125.100', port=5001)
