from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    admin = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, admin=False, **kwargs):
        kwargs['name'] = kwargs['name'].lower()
        kwargs['password'] = generate_password_hash(kwargs['password'])

        super(User, self).__init__(admin=admin, **kwargs)

    def __repr__(self):
        return '<User: %r>' % self.name

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password, password)


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False, unique=True)
    exists = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return '<File: %r>' % self.path


class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)

    def __repr__(self):
        return '<Status: %r>' % self.name


class Software(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    path = db.Column(db.String(255), nullable=False, unique=True)
    exists = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return '<Software: %r>' % self.name


class Suite(db.Model):
    id = db.Column(db.Integer, primary_key=True)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time_created = db.Column(db.DateTime, default=datetime.now, nullable=False)
    time_update = db.Column(db.DateTime, onupdate=datetime.now)
    status_id = db.Column(db.Integer, db.ForeignKey('status.id', ondelete='SET NULL'), nullable=False)
    status = db.relationship('Status', backref=db.backref('tasks', lazy=True, cascade="all, delete-orphan"))
    file_id = db.Column(db.Integer, db.ForeignKey('file.id', ondelete='SET NULL'), nullable=False)
    file = db.relationship('File', backref=db.backref('tasks', lazy=True, cascade="all, delete-orphan"))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    user = db.relationship('User', backref=db.backref('tasks', lazy=True, cascade="all, delete-orphan"))
    software_id = db.Column(db.Integer, db.ForeignKey('software.id', ondelete='SET NULL'), nullable=False)
    software = db.relationship('Software', backref=db.backref('tasks', lazy=True, cascade='all, delete-orphan'))
    suite_id = db.Column(db.Integer, db.ForeignKey('suite.id', ondelete='SET NULL'), nullable=True)
    suite = db.relationship('Suite', backref=db.backref('tasks', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return '<Task id:%r status:%r>' % (self.id, self.status)
