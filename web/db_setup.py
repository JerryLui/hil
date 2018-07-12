from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine


Base = declarative_base()


class File(Base):
    __tablename__ = 'File'
    id = Column(Integer, primary_key=True)
    file_name = Column(String(250), nullable=False)
    file_path = Column(String(250), nullable=False)

    def __repr__(self):
        return '<File %r>' % self.file_path


class Task(Base):
    __tablename__ = 'Task'
    id = Column(Integer, primary_key=True)
    status = Column(Integer, nullable=False)
    file_id = Column(Integer, ForeignKey('File.id'))
    file = relationship(File)

    def __repr__(self):
        return '<Task id:%r status:%r>' % (self.id, self.status)


engine = create_engine('sqlite:///static/db/database.db')
Base.metadata.create_all(engine)
