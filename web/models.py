from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class File(Base):
    __tablename__ = 'File'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    path = Column(String(250), nullable=False)
    tasks = relationship('Task')

    def __repr__(self):
        return '<File %r>' % self.file_path


class User(Base):
    __tablename__ = 'User'
    id = Column(Integer, primary_key=True)
    name = Column(String(32), unique=True, nullable=False)
    password = Column(String(32), nullable=False)
    tasks = relationship('Task')


class Task(Base):
    __tablename__ = 'Task'
    id = Column(Integer, primary_key=True)
    time_created = Column(DateTime, server_default=func.now())
    time_update = Column(DateTime, onupdate=func.now())
    status = Column(Integer, nullable=False)
    file_id = Column(Integer, ForeignKey('File.id'), nullable=False)
    file = relationship('File', foreign_keys=file_id)
    user_id = Column(Integer, ForeignKey('User.id'), nullable=False)
    user = relationship('User', foreign_keys=user_id)

    def __repr__(self):
        return '<Task id:%r status:%r>' % (self.id, self.status)


engine = create_engine('sqlite:///static/db/database.db')
Base.metadata.create_all(engine)
