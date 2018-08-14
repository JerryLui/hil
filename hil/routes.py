from flask import Flask, render_template, flash, session, redirect, url_for, request, jsonify
from flask import send_from_directory, send_file
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import func
from werkzeug.utils import secure_filename
from multiprocessing import Lock, Pipe, Process, set_start_method

import os
import sys

# Package specific imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import db, Task, File, User, Status, Suite
from forms import TaskForm, UserForm, FileForm, PasswordForm
from handlers import Worker


app = Flask('hil')
app.debug = True

# -------------------- DEVICE CONFIGURATION --------------------
# Configure the following to fit the device
app.config['DEVICE_HOST'] = '10.239.124.134'    # Listening address, use device LAN-address
app.config['DEVICE_PORT'] = 5005                # Port, ambiguous
app.config['DEVICE_LOG_DRIVE'] = r'C:\Users\JerryL\Downloads\Archives'  # Drive where the log files are stored

# Initialization parameters, used for first run.
app.config['CREATE_ADMIN'] = True                           # create an admin user during init
app.config['ADMIN_CREDENTIALS'] = {'password': 'admin123'}  # admin credentials
app.config['CREATE_DIRECTORIES'] = True                     # create empty directories for future use


# -------------------- APPLICATION CONFIGURATION --------------------
# Server configuration
# Ensure db folder exists in static
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///static/db/database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Application configuration
app.secret_key = 'a3067a6f5bc2b743c88ef8'
app.config['PROJECT_FOLDER'] = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['PROJECT_FOLDER'], 'tmp', 'uploads')

# Process handling configuration
app.config['OPS_LOCK'] = Lock()
app.config['OPS_PIPE_PARENT'] = dict()
app.config['OPS_PIPE_CHILD'] = dict()
app.config['OPS_PROCESS'] = dict()

app.config['FILE_UPDATE_PROCESS'] = None

# None at 0 to match table indexing.
app.config['STATUS_DICT'] = [None, 'Waiting', 'Starting', 'Running', 'Finished', 'Failed', 'Error']

db.init_app(app)
app.app_context().push()


# -------------------- ROUTES --------------------
@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def view_index(form=None):
    """ VIEW: Index page to handle registration, login and task creation """
    # TODO: Multiselect task create
    if session.get('user_name'):
        if form:
            if form._prefix == 'log-':
                suite_form = _get_task_suite_form()
                form = (form, suite_form)
            elif form._prefix == 'suite-':
                log_form = _get_task_log_form()
                form = (log_form, form)
        else:
            log_form = _get_task_log_form()
            suite_form = _get_task_suite_form()

            form = (log_form, suite_form)
    else:
        # Render forms for registration/login if no session
        if form:    # Enables flash messages when called by another function
            if form._prefix == 'login-':
                form = (form, UserForm(prefix='register'))
            elif form._prefix == 'register-':
                form = (UserForm(prefix='login'), form)
        else:
            form = (UserForm(prefix='login'), UserForm(prefix='register'))
    return render_template('index.html',
                           form=form,
                           tasks=Task.query.order_by(Task.time_created.desc()).limit(30).all(),
                           active='index')


@app.route('/history')
def view_history():
    """ VIEW: Log of all tasks """
    # TODO: Implement with page hopping and next page btn etc.
    return render_template('history.html', active='history', tasks=Task.query.order_by(Task.time_created.desc()).all())


@app.route('/about')
def view_info():
    """ VIEW: Information regarding site and author """
    return render_template('about.html', active='about')


@app.route('/home')
def view_home():
    """ VIEW: User homepage, shows log of all tasks created by user """
    if session.get('user_name'):
        user = User.query.filter_by(name=session['user_name']).first()
        return render_template('home.html', tasks=user.tasks, admin=user.admin)
    else:
        return redirect(url_for('view_index'))


@app.route('/task/<int:pid>')
def view_task(pid):
    """ VIEW: Task specific information """
    task = Task.query.filter_by(id=pid).first()
    if task:
        log_text = get_log_text(task.file.path, task.id)
        return render_template('task.html', task=task, text=log_text)
    else:
        flash('Task not found.', 'warning')
        return redirect(url_for('view_index'))


@app.route('/suite/<int:sid>')
def view_suite(sid):
    """ VIEW: Suite info page """
    suite = Suite.query.filter_by(id=sid).first()
    if suite:
        return render_template('suite.html', suite=suite)
    else:
        flash('Suite not found.', 'warning')
        return redirect(url_for('view_index'))


@app.route('/change-password', methods=['GET', 'POST'])
def view_password():
    user_name = session.get('user_name')
    if not user_name:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('view_index'))

    form = PasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(name=user_name).first()
        if user.verify_password(form.current_password.data):
            user.set_password(form.new_password.data)
            db.session.commit()
            flash('Password update successful!', 'success')
            return redirect(url_for('view_home'))
        else:
            flash('Incorrect password!', 'warning')
    return render_template('password.html', form=form)


@app.errorhandler(404)
@app.errorhandler(405)
def view_error(msg):
    """ VIEW: Errorhandling """
    return render_template('error.html', error=msg)


# -------------------- OPERATIONS --------------------
@app.route('/task/update/all')
def update_all_tasks():
    """
    Updates current task status of all active tasks

    :return : dict
    Javascript friendly jsonified dictionary of all active tasks with its' respective status.
    """
    # TODO: Schedule this function after starting a task (replace if with while loop with sleep inside)
    active_dict = dict()

    # Use list to avoid "RuntimeError: dictionary changed size during iteration"
    for pid in list(app.config['OPS_PIPE_PARENT'].keys()):
        if update_task(pid):
            task = Task.query.filter_by(id=pid).first()
            active_dict[pid] = task.status.name

    return jsonify(active_dict)


def update_task(pid):
    """
    Polls the process with pid for information regarding its' progress.

    :return : bool
    Whether or not the process at pid is still alive.
    """
    process = app.config['OPS_PROCESS'].get(pid)
    parent = app.config['OPS_PIPE_PARENT'].get(pid)

    if not parent:
        return False

    try:
        if parent.poll() or process.is_alive():
            if parent.poll():
                status_id = parent.recv()

                task = Task.query.filter_by(id=pid).first()
                if task.status_id != status_id:
                    task.status_id = status_id
                    db.session.commit()
        else:
            raise EOFError()
        return True
    except (OSError, EOFError, BrokenPipeError):
        pass
    # Close parent pipe and delete pipes from dict
    parent.close()
    del app.config['OPS_PIPE_PARENT'][pid], app.config['OPS_PIPE_CHILD'][pid]
    return False


@app.route('/create/<option>', methods=['POST'])
def create_task(option):
    """
    Create a task and insert to db
    """
    if option == 'suite':
        form = _get_task_suite_form()
    elif option == 'log':
        form = _get_task_log_form()
    else:
        flash('Invalid request!', 'danger')
        return redirect(url_for('view_index'))

    if not form.validate_on_submit():
        flash('Invalid submission!', 'warning')
        return view_index(form)
    else:
        try:
            # Create new task with user and file and submit it to DB
            user = User.query.filter_by(name=session['user_name']).first()
            if option == 'suite':
                files = File.query.filter(File.path.startswith(form.file_name.data)).all()

                # New suite path
                new_suite = Suite()
                db.session.add(new_suite)
                db.session.commit()

                suite_id = new_suite.id
            else:
                files = [File.query.filter_by(name=form.file_name.data).first()]
                suite_id = 1

            for file in files:
                new_task = Task(status_id=1, file_id=file.id, user_id=user.id, suite_id=suite_id)
                db.session.add(new_task)
                db.session.commit()

                # Start new process
                app.config['OPS_PIPE_PARENT'][new_task.id], app.config['OPS_PIPE_CHILD'][new_task.id] = Pipe(duplex=False)
                app.config['OPS_PROCESS'][new_task.id] = Worker(new_task.file.path,
                                                                     new_task.id,
                                                                     get_log_path(new_task.file.path, new_task.id),
                                                                     app.config['OPS_LOCK'],
                                                                     app.config['OPS_PIPE_CHILD'][new_task.id])
                app.config['OPS_PROCESS'][new_task.id].start()
                app.logger.info('%s created new task on file %s', user.name, file.name)
            flash('Task(s) created!', 'success')

        except Exception as xcpt:
            db.session.rollback()
            app.logger.exception('%s raised with file %s: \n' + str(xcpt), session['user_name'], form.file_name)
            flash(str(xcpt), 'danger')
    return redirect(url_for('view_index'))


@app.route('/register', methods=['POST'])
def create_user():
    """
    Create a user and insert to db
    """
    form = UserForm(prefix='register')

    if not form.validate_on_submit():
        flash('Invalid input.', 'warning')
        return view_index(form)
    else:
        user, exists = db_insert_or_get(User, name=form.name.data, defaults={'password': form.password.data})
        if exists:
            flash('Username taken.', 'warning')
        else:
            db.session.commit()

            session['user_name'] = user.name
            app.logger.info('User %s created successfully.', user.name)
            flash('User created successfully.', 'success')

    return redirect(url_for('view_index'))


@app.route('/login', methods=['POST'])
def create_session():
    """
    Validate login and create session
    """
    form = UserForm(prefix='login')

    if not form.validate_on_submit():
        flash('Invalid input.', 'warning')
        return view_index(form)
    else:
        user_name = form.name.data.lower()
        user_password = form.password.data

        user = db.session.query(User).filter_by(name=user_name).first()
        if user is not None and user.verify_password(user_password):
            session['user_name'] = user_name
            app.logger.info('%s logged in successfully.', user_name)
            flash('Login successful.', 'success')
        else:
            app.logger.info('%s tried to log in unsuccessfully.', user_name)
            flash('Incorrect login credentials.', 'warning')
    return redirect(url_for('view_index'))


@app.route('/update/db')
def db_update_files():
    """
    Parallel way of updating file list
    """
    # TODO: Implement better way of detecting changes in file storage.
    try:
        if not app.config['FILE_UPDATE_PROCESS'].is_alive():
            app.config['FILE_UPDATE_PROCESS'] = Process(target=_populate_table_file())
            app.config['FILE_UPDATE_PROCESS'].start()
    except AttributeError:
        pass
    return redirect(url_for('view_index'))


@app.route('/download/log/<task_id>')
def download_log(task_id):
    """ Gives download file """
    task = Task.query.filter_by(id=task_id).first()
    log_path = get_log_path(task.file.path, task.id)
    return send_file(log_path, as_attachment=True)


@app.route('/logout')
def logout():
    session.pop('user_name', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('view_index'))


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static/img', 'favicon.ico', mimetype='image/vnd.microsoft.icon')


# -------------------- HELPERS --------------------
def get_log_path(file_path, task_id):
    """
    :return : path
    The path to log file associated with given file_path and task_id
    """
    return ''.join([os.path.splitext(file_path)[0], '_', str(task_id), '.log'])


def get_log_text(file_path, task_id):
    """
    :return : str
    List of log text entries in log file
    """
    with open(get_log_path(file_path, task_id), 'r') as f:
        return f.readlines()


def _sort_by_folder(file_list):
    """
    :return : dict
    Dict sorted by file directories with list of directory contents as value
    """
    sorted_dict = dict()
    for file in file_list:
        file_dir = os.path.dirname(file.path)
        if sorted_dict.get(file_dir):
            sorted_dict.get(file_dir).append(file)
        else:
            sorted_dict[file_dir] = [file]
    return sorted_dict


def _get_task_log_form():
    return TaskForm([(file.name, file.name) for file in File.query.all()], prefix='log')


def _get_task_suite_form():
    return TaskForm([(k, os.path.split(k)[1]) for k in _sort_by_folder(File.query.all())], prefix='suite')


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
    """ Populates File table by running _recursive_log_scan on DEVICE_LOG_FOLDER """
    [db_insert_or_get(File, name=log.name, path=log.path) for log in _recursive_log_scan()]
    db.session.commit()


def _populate_table_status():
    """ Insert STATUS_DICT into Status table """
    [db_insert_or_get(Status, name=name) for name in app.config['STATUS_DICT'][1:]]
    db.session.commit()


def _populate_table_suite():
    """ Add base suite to Suite table """
    db_insert_or_get(Suite, id=1)
    db.session.commit()


def _recursive_log_scan(directory=None):
    """ Iterator of all files ending with dvl in log_drive """
    directory = directory or app.config['DEVICE_LOG_DRIVE']

    for entry in os.scandir(directory):
        if entry.is_dir(follow_symlinks=False):
            yield from _recursive_log_scan(entry)
        elif os.path.splitext(entry.name)[1] == '.dvl':
            yield entry


# -------------------- ADMIN --------------------
class SessionModelView(ModelView):
    """ User authentication for admin view"""
    def is_accessible(self):
        user_name = session.get('user_name')
        if not user_name:
            return False
        return User.query.filter_by(name=user_name).first().admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('view_index'))


class AdminHomeView(AdminIndexView):
    @expose('/')
    def index(self):
        """ VIEW: Admin index page """
        return self.render('admin/index.html')

    @expose('/upload', methods=['POST', 'GET'])
    def upload(self):
        """ VIEW: Upload page """
        if session.get('user_name'):
            form = FileForm()
            if request.method == 'POST':
                if form.validate():
                    try:
                        file = form.file.data
                        file_name = secure_filename(file.filename)
                        if form.path.data:
                            if os.path.isdir(form.path.data):
                                file.save(form.path.data, file_name)
                            else:
                                os.makedirs(form.path.data)
                                file.save(form.path.data, file_name)
                        else:
                            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name))
                        flash('File uploaded successfully.', 'success')
                    except Exception as exc:
                        flash('File upload failed: ' + str(exc), 'danger')
                else:
                    flash('Invalid file!', 'warning')
            return self.render('admin/upload.html', form=form)
        else:
            return redirect(url_for('view_index'))

    def is_accessible(self):
        user_name = session.get('user_name')
        if not user_name:
            return False
        return User.query.filter_by(name=user_name).first().admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('view_index'))


# -------------------- MAIN --------------------
if __name__ == '__main__':
    # Initial preparations, should probably refactor into separate config and create_app files
    db.create_all()
    _populate_table_file()
    _populate_table_status()
    _populate_table_suite()

    # Create an Admin user
    if app.config['CREATE_ADMIN']:
        user, exists = db_insert_or_get(User, name='admin', defaults={'password': 'admin123'}, admin=True)
        db.session.commit()

    # Creates empty folders for use if they don't exist
    if app.config['CREATE_DIRECTORIES']:
        for folder in (os.path.join(app.config['PROJECT_FOLDER'], 'tmp', 'uploads'), \
                       os.path.join(app.config['PROJECT_FOLDER'], 'static', 'db')):
            try:
                os.makedirs(folder)
            except OSError as xcpt:
                pass

    # Add DB views
    admin = Admin(index_view=AdminHomeView(), template_mode='bootstrap3')
    admin.add_views(SessionModelView(User, db.session),
                    SessionModelView(File, db.session),
                    SessionModelView(Task, db.session),
                    SessionModelView(Suite, db.session),
                    SessionModelView(Status, db.session))
    admin.init_app(app)

    # Start the server
    app.run(host=app.config['DEVICE_HOST'], port=app.config['DEVICE_PORT'])
