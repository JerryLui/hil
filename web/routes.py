from flask import Flask, render_template, send_from_directory, flash, session, redirect, url_for, request
from flask_admin import Admin, BaseView, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from werkzeug.utils import secure_filename
from werkzeug.contrib.fixers import ProxyFix

import os
import sys

# Package specific imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import db, Task, File, User, Status
from forms import TaskForm, UserForm, FileForm

# -------------------- APPLICATION CONFIGURATION --------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///static/db/database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.wsgi_app = ProxyFix(app.wsgi_app)
app.secret_key = 'a3067a6f5bc2b743c88ef8'
app.config['PROJECT_FOLDER'] = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['PROJECT_FOLDER'], 'tmp', 'uploads')
app.config['LOG_DRIVE'] = r'C:\Users\JerryL\Downloads\Archives'

db.init_app(app)
app.app_context().push()


# -------------------- ROUTES --------------------
@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def page_index(form=None):
    if session.get('user_name'):
        form = TaskForm([(file.name, file.name) for file in File.query.all()])
    else:
        if form:
            if form._prefix == 'login-':
                form = (form, UserForm(prefix='register'))
            elif form._prefix == 'register-':
                form = (UserForm(prefix='login'), form)
        else:
            form = (UserForm(prefix='login'), UserForm(prefix='register'))
    return render_template('index.html',
                           form=form,
                           tasks=Task.query.order_by(Task.time_created).all(),
                           active='index')


@app.route('/active')
def page_active():
    return render_template('active.html', active='active', tasks=Task.query.order_by(Task.time_created).all())


@app.route('/about')
def page_info():
    return render_template('about.html', active='about')


@app.route('/home')
def page_home():
    if session.get('user_name'):
        return render_template('home.html', tasks=User.query.filter_by(name=session['user_name']).first().tasks)
    else:
        return redirect(url_for('page_index'))


@app.route('/task/<int:id>')
def page_task(id):
    if session.get('user_name'):
        return render_template('task.html', active='task', task=Task.query.filter_by(id=id).first())
    else:
        return redirect(url_for('page_index'))


@app.errorhandler(404)
@app.errorhandler(405)
def error(msg):
    return render_template('error.html', error=msg)


# -------------------- OPERATIONS --------------------
@app.route('/create', methods=['POST'])
def create_task():
    form = TaskForm([(file.name, file.name) for file in File.query.all()])

    if not form.validate():
        flash('Invalid options!', 'warning')
    else:
        try:
            user = db.session.query(User).filter_by(name=session['user_name']).first()
            file = db.session.query(File).filter_by(name=form.file_name.data).first()
            new_task = Task(status_id=1, file_id=file.id, user_id=user.id)
            db.session.add(new_task)
            db.session.commit()
            flash('Task created!', 'success')
        except Exception as xcpt:
            db.session.rollback()
            print(xcpt)
    return page_index(form)


@app.route('/register', methods=['POST'])
def create_user():
    form = UserForm(prefix='register')

    if not form.validate():
        flash('Invalid input.', 'warning')
    else:
        user, exists = db_insert_or_get(User, name=form.name.data, defaults={'password': form.password.data})
        if exists:
            flash('Username taken.', 'warning')
        else:
            db.session.commit()

            session['user_name'] = user.name
            flash('User created successfully.', 'success')

    return page_index(form)


@app.route('/login', methods=['POST'])
def create_session():
    form = UserForm(prefix='login')

    if not form.validate():
        flash('Invalid input.', 'warning')
    else:
        user_name = form.name.data
        user_password = form.password.data

        user = db.session.query(User).filter_by(name=user_name).first()
        if user is not None and user.check_password(user_password):
            session['user_name'] = user_name
            flash('Login successful.', 'success')
        else:
            flash('Incorrect login credentials.', 'warning')
    return page_index(form)


@app.route('/logout')
def logout():
    session.pop('user_name', None)
    return redirect(url_for('page_index'))


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static/img', 'favicon.ico', mimetype='image/vnd.microsoft.icon')


# -------------------- DATABASE --------------------
def db_insert_or_get(model, defaults=None, **kwargs):
    """
    Gets or inserts model into db wether or not if it exists or not.
    :rtype: db.Model
    :returns : (db.Model, bool)
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


def _populate_table_status():
    [db_insert_or_get(Status, name=name) for name in ('Waiting', 'Starting', 'Running', 'Finished', 'Failed', 'Error')]
    db.session.commit()


def _recursive_log_scan(directory=app.config['LOG_DRIVE']):
    """ Iterator of all files ending with dvl in log_drive """
    for entry in os.scandir(directory):
        if entry.is_dir(follow_symlinks=False):
            yield from _recursive_log_scan(entry)
        elif os.path.splitext(entry)[1] == '.dvl':
            yield entry


# -------------------- DB FILE --------------------

# -------------------- ADMIN --------------------
class SessionModelView(ModelView):
    """ Authenticates user for acces admin page. """
    def is_accessible(self):
        return session.get('user_name') == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('page_index'))


class AdminHomeView(AdminIndexView):
    """ Admin frontpage view. """
    @expose('/')
    def index(self):
        if session.get('user_name') == 'admin':
            return self.render('admin/index.html')
        else:
            return redirect(url_for('page_index'))


# class UploadFileView(BaseView):
#     @expose('/', methods=['POST', 'GET'])
#     def index(self):
#         if session.get('user_name'):
#             form = FileForm()
#             if request.method == 'POST':
#                 if form.validate():
#                     file = form.file.data
#                     file_name = secure_filename(file.filename)
#                     file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name))
#                     flash('File uploaded successfully.', 'success')
#                 else:
#                     flash('Invalid file!', 'warning')
#             return self.render('admin/upload.html', form=form)
#         else:
#             return redirect(url_for('page_index'))


# -------------------- MAIN --------------------
if __name__ == '__main__':
    db.create_all()
    _populate_table_file()
    _populate_table_status()

    admin = Admin(index_view=AdminHomeView(), template_mode='bootstrap3')
    admin.add_views(SessionModelView(User, db.session),
                    SessionModelView(File, db.session),
                    SessionModelView(Task, db.session),
                    SessionModelView(Status, db.session))
    admin.init_app(app)

    app.run(host='10.239.125.100', port=5001, debug=True)
