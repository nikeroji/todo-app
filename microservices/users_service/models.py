from sqlalchemy import Column, DateTime, Integer, String, func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    name = Column(
        String(100),
        nullable=False,
    )

    email = Column(
        String(254),
        nullable=False,
        unique=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
