from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. Every model in database/models/ inherits from
    this so Alembic's autogenerate can see the full metadata in one place."""
