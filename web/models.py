from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

# TODO: TEST DB Structure
class File(Base):
    __tablename__ = 'File'
    id = Column(Integer, primary_key=True)
    file_name = Column(String(250), nullable=False)
    file_path = Column(String(250), nullable=False)
    tasks = relationship('Task')

    def __repr__(self):
        return '<File %r>' % self.file_path


class Status(Base):
    __tablename__ = 'Status'
    id = Column(Integer, primary_key=True)
    name = Column(String(32), unique=True)
    tasks = relationship('Task')


class User(Base):
    __tablename__ = 'User'
    id = Column(Integer, primary_key=True)
    name = Column(String(32))
    tasks = relationship('Task')


class Task(Base):
    __tablename__ = 'Task'
    id = Column(Integer, primary_key=True)
    user = Column(Integer, ForeignKey('User.id'), nullable=False)
    time = Column(DateTime, nullable=False)
    status = Column(Integer, ForeignKey('Status.id'), nullable=False)
    file_id = Column(Integer, ForeignKey('File.id'), nullable=False)

    def __repr__(self):
        return '<Task id:%r status:%r>' % (self.id, self.status)


engine = create_engine('sqlite:///static/db/database.db')
Base.metadata.create_all(engine)
