from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text, func

from database import Base


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    is_completed = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        server_default=func.now(),
    )

    due_date = Column(Date, nullable=True)
