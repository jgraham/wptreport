from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey, Integer, String

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, relationship

Session = sessionmaker(expire_on_commit=False)

Base = declarative_base()


class Status(Base):
    __tablename__ = "status"

    id = Column(Integer, primary_key=True)
    name = Column(String)


class Run(Base):
    __tablename__ = "run"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    info = Column(String)


class Test(Base):
    __tablename__ = "test"

    id = Column(Integer, primary_key=True)
    test = Column(String)
    subtest = Column(String)


class Result(Base):
    __tablename__ = "result"

    run_id = Column(Integer, ForeignKey(Run.id), primary_key=True)
    test_id = Column(Integer, ForeignKey(Test.id), primary_key=True)
    status_id = Column(Integer, ForeignKey(Status.id))

    run = relationship(Run)
    test = relationship(Test)
    status = relationship(Status)

def init(file_name):
    engine = create_engine('sqlite:///%s' % file_name)
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)
