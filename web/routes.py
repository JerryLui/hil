from flask import Flask, render_template, request, send_from_directory, flash, get_flashed_messages, redirect
from multiprocessing import Pipe, Process
from werkzeug.utils import secure_filename
from werkzeug.contrib.fixers import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired
from wtforms import StringField, SelectField, SubmitField, PasswordField
import time
import random
import os
import sys

# Package specific imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import Task, File, User

# -------------------- APPLICATION CONFIGURATION --------------------
app = Flask(__name__)
app.debug = True
app.wsgi_app = ProxyFix(app.wsgi_app)
app.secret_key = 'a3067a6f5bc2b743c88ef8'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///static/db/database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PROJECT_FOLDER'] = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['PROJECT_FOLDER'], 'tmp')
app.config['LOG_DRIVE'] = r'C:\Users\JerryL\Downloads\Archives'
app.config['STATUS_CODE'] = {-1: 'Failed', 0: 'Waiting', 1: 'Running', 2: 'Finished'}
db = SQLAlchemy(app)


# -------------------- FLASK --------------------
@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    return render_template('index.html', form=TaskForm(), tasks=db.session.query(Task).all())


@app.route('/create', methods=['POST'])
def create_task():
    form = TaskForm()

    if request.method == 'POST':
        if form.validate() == False:
            flash('Invalid options!', 'warning')
        else:
            try:
                user = get_or_insert(User, name=form.user_name.data, password=form.user_password.data)
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
    form = UserForm()


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static/img', 'favicon.ico', mimetype='image/vnd.microsoft.icon')


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
        return render_template('upload.html', 'warning')


# -------------------- DATABASE --------------------
def get_or_insert(model, defaults=None, **kwargs):
    instance = db.session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        kwargs.update(defaults or {})
        instance = model(**kwargs)
        db.session.add(instance)
        db.session.flush()
        return instance


def _populate_table_file():
    [db.session.merge(File(name=log.name, path=log.path)) for log in _recursive_log_scan()]
    db.session.commit()


def _recursive_log_scan(directory=app.config['LOG_DRIVE']):
    """ Iterator of all files ending with dvl in log_drive """
    for entry in os.scandir(directory):
        if entry.is_dir(follow_symlinks=False):
            yield from _recursive_log_scan(entry)
        elif os.path.splitext(entry)[1] == '.dvl':
            yield entry


# -------------------- FORMS --------------------
class TaskForm(FlaskForm):
    file_name = SelectField(
            'Select file',
            choices=[(file.name, file.name) for file in db.session.query(File).all()],
            validators=[DataRequired("PLease select a file")]
    )
    submit = SubmitField('Submit')


class UserForm(FlaskForm):
    user_name = StringField(
            'NetID',
            validators=[DataRequired("Please enter your username.")]
    )
    user_password = PasswordField(
            'Password',
            validators=[DataRequired("Please enter your password.")]
    )
    submit = SubmitField('Register')

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
    _populate_table_file()
    app.run(host='10.239.125.100', port=5001)
