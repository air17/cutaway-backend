from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String(50), unique=True)
    email = Column(String(50), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    username = Column(String(50), unique=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    about = Column(String(10000))
    user_pic = Column(String(100))
    bg_pic = Column(String(100))

    link = relationship("Link", back_populates="user", cascade="all, delete", passive_deletes=True)


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(30), nullable=False)
    link = Column(String(100), nullable=False)
    additional = Column(Boolean, default=False, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="link")
