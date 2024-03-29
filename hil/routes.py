from flask import Flask, render_template, flash, session, redirect, url_for, request, jsonify
from flask import send_from_directory, send_file
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from werkzeug.utils import secure_filename
from multiprocessing import Lock, Pipe, Process, Pool

import os
import sys

# Package specific imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import db, Task, File, User, Status, Software
from forms import TaskForm, UserForm, FileForm, PasswordForm
from handlers import Worker

# TODO: Convert to SETUP SCRIPT
# TODO: Fix table string shortening on VIEW
app = Flask('hil')
app.debug = True

# -------------------- DEVICE CONFIGURATION --------------------
# Configure the following to fit the device
app.config['DEVICE_HOST'] = ''  # Listening address, use device LAN-address
app.config['DEVICE_PORT'] = 5005  # Port, ambiguous
app.config['DEVICE_LOG_DRIVE'] = r'C:\Users\JerryL\Downloads\Archives'  # Drive where the log files are stored
app.config['DEVICE_SW_DRIVE'] = r'C:\Users\JerryL\Downloads\Archives\Software'

# Initialization parameters, used for first run.
app.config['CREATE_ADMIN'] = True  # create an admin user during init
app.config['ADMIN_CREDENTIALS'] = {'password': 'admin123'}  # admin credentials
app.config['CREATE_DIRECTORIES'] = True  # create empty directories for future use

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
    # Form selection
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
        if form:  # Enables flash messages when called by another function
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
        return render_template('task.html', task=task, text=get_log_text(task))
    else:
        flash('Task not found.', 'warning')
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
            software = Software.query.filter_by(name=form.software.data).first()

            if option == 'suite':
                files = File.query.filter(File.path.startswith(form.file.data)).filter_by(stored=True).all()

                # Filter out subfolders
                files = [file for file in files if os.path.split(file.path)[0] == form.file.data]

                if not files:
                    raise FileNotFoundError(2, 'No files found in suite.')

            else:
                files = [File.query.filter_by(name=form.file.data, stored=True).first()]

            # Create and insert new task
            new_task = Task(status_id=1, user=user, software=software)
            [new_task.files.append(file) for file in files]

            db.session.add(new_task)
            db.session.commit()

            # Start new process
            app.config['OPS_PIPE_PARENT'][new_task.id], app.config['OPS_PIPE_CHILD'][new_task.id] = Pipe(duplex=False)
            app.config['OPS_PROCESS'][new_task.id] = Worker([file.path for file in new_task.files],
                                                            new_task.software.path,
                                                            new_task.id,
                                                            get_log_path(new_task),
                                                            app.config['OPS_LOCK'],
                                                            app.config['OPS_PIPE_CHILD'][new_task.id])
            app.config['OPS_PROCESS'][new_task.id].start()
            app.logger.info('%s created new task %i.' % (user.name, new_task.id))
            flash('Task(s) created!', 'success')

        except Exception as xcpt:
            db.session.rollback()
            app.logger.exception('%s raised with file %s: \n' + str(xcpt), session['user_name'], form.file)
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
    _populate_table_files(File)
    _populate_table_files(Software)
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


@app.template_filter('dirname')
def dirname(pathlike):
    return os.path.split(os.path.dirname(pathlike))[1]


# -------------------- HELPERS --------------------
def get_log_path(task):
    """
    :return : path
    The path to log file associated with given file_path and task_id
    """
    if len(task.files) > 1:
        return os.path.join(os.path.dirname(task.files[0].path), task.software.name + '_' + str(task.id) + '.log')
    else:
        return ''.join([os.path.splitext(task.files[0].path)[0], '_', str(task.id), '.log'])


def get_log_text(task):
    """
    :return : str
    List of log text entries in log file
    """
    with open(get_log_path(task), 'r') as f:
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
    """
    :return : TaskForm
    Task form with log files as file choice
    """
    files = [file.name for file in File.query.filter_by(stored=True).order_by(File.name).all()]
    return TaskForm(file_choices=list(zip(files, files)),
                    sw_choices=[(sw.name, sw.name) for sw in Software.query.order_by(Software.name).all()],
                    prefix='log')


def _get_task_suite_form():
    """
    :return : TaskForm
    Task form with log folders as file choice
    """
    folders = _sort_by_folder(File.query.filter_by(stored=True).order_by(File.name).all())
    return TaskForm(file_choices=[(folder, os.path.split(folder)[1]) for folder in folders],
                    sw_choices=[(sw.name, sw.name) for sw in Software.query.order_by(Software.name).all()],
                    prefix='suite')


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


def _populate_table_files(model):
    """ Populates File or Software table. """
    # Get list of all files
    if model is Software:
        paths_found = {path.path for path in _recursive_scan(app.config['DEVICE_SW_DRIVE'], '.exe')}
    elif model is File:
        paths_found = {path.path for path in _recursive_scan()}
    else:
        raise TypeError('Type of File or Software expected as model.')
    paths_existing = {file.path for file in model.query.all()}

    # Paths that have been deleted from host but still exist in DB
    for path in paths_existing - paths_found:
        model.query.filter_by(path=path).update({'stored': False})

    # Paths that are found and exists in DB
    for path in paths_found.intersection(paths_existing):
        model.query.filter_by(path=path).update({'stored': True})

    # Paths found that doesn't exist in the DB
    paths_new = paths_found - paths_existing
    for path in paths_new:
        name = os.path.split(path)[1]
        new_model = model(name=name, path=path)
        db.session.add(new_model)

    db.session.commit()


def _populate_table_status():
    """ Insert STATUS_DICT into Status table """
    [db_insert_or_get(Status, name=name) for name in app.config['STATUS_DICT'][1:]]
    db.session.commit()


def _recursive_scan(directory=None, file_extension='.dvl'):
    """ Iterator of all files ending with dvl in log_drive """
    directory = directory or app.config['DEVICE_LOG_DRIVE']

    for entry in os.scandir(directory):
        if entry.is_dir(follow_symlinks=False):
            yield from _recursive_scan(entry)
        elif os.path.splitext(entry.name)[1] == file_extension:
            yield entry


# -------------------- ADMIN --------------------
class SessionModelView(ModelView):
    def __init__(self, model, session, column_list=None, **kwargs):
        self.column_list = column_list
        super(SessionModelView, self).__init__(model, session, **kwargs)

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
    _populate_table_files(File)
    _populate_table_status()
    _populate_table_files(Software)

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
                    SessionModelView(Software, db.session),
                    SessionModelView(Status, db.session, column_list=('id', 'name')))
    admin.init_app(app)

    # Start the server
    app.run(host=app.config['DEVICE_HOST'], port=app.config['DEVICE_PORT'])
