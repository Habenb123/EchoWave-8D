from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey

from database import Base

from datetime import datetime


class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True)

    email = Column(String, unique=True)

    password = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)


class ProcessingJob(Base):

    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    filename = Column(String)

    status = Column(String)

    output = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)