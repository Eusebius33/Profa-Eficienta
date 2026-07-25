"""
SQLAlchemy data layer for the app: engine, session factory, and ORM models
for PostgreSQL (migrated from profu.db).
"""
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy import ForeignKey, String, Text, DateTime, create_engine, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    scoped_session,
    sessionmaker,
)


class RowMixin:
    """Makes ORM rows readable the same way the old sqlite3.Row objects were
    (row["col"], row.get("col"), "col" in row.keys(), dict(row)) so the
    existing view/template code didn't need to change everywhere it reads a row."""

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def keys(self):
        return self.__table__.columns.keys()


class Base(DeclarativeBase):
    pass


class User(RowMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hash: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)
    gender: Mapped[str] = mapped_column(String, nullable=False)
    tehnologie: Mapped[str] = mapped_column(String, nullable=False)
    liceu: Mapped[str] = mapped_column(String, nullable=False)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    styles: Mapped[list["Style"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Style(RowMixin, Base):
    __tablename__ = "styles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    style_name: Mapped[str] = mapped_column(String, nullable=False)
    test_type: Mapped[str] = mapped_column(String, nullable=False)
    style_description: Mapped[str] = mapped_column(Text, nullable=False)
    documents: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    user: Mapped["User"] = relationship(back_populates="styles")


class Document(RowMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False, default="Document nou")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    user: Mapped["User"] = relationship(back_populates="documents")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="document")


class Conversation(RowMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    style_id: Mapped[Optional[int]] = mapped_column(ForeignKey("styles.id"))
    school_class: Mapped[Optional[str]] = mapped_column(String)
    bac: Mapped[Optional[str]] = mapped_column(String)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id"))

    user: Mapped["User"] = relationship(back_populates="conversations")
    style: Mapped[Optional["Style"]] = relationship()
    document: Mapped[Optional["Document"]] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.id"
    )

    @property
    def style_description(self):
        """Mirrors the old `LEFT JOIN styles ON conversations.style_id = styles.id`
        queries that pulled style_description onto the conversation row."""
        return self.style.style_description if self.style else None

    def keys(self):
        return [*self.__table__.columns.keys(), "style_description"]


class Message(RowMixin, Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String)
    style_id: Mapped[Optional[str]] = mapped_column(String)
    school_class: Mapped[Optional[str]] = mapped_column(String)
    bac: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    action_type: Mapped[Optional[str]] = mapped_column(String)
    exam_data: Mapped[Optional[str]] = mapped_column(Text)
    doc_action: Mapped[Optional[str]] = mapped_column(String)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


# Functia de creare a Engine-ului PostgreSQL
def get_engine(url):
    if not database_exists(url):
        create_database(url)
    pool_size = int(os.environ.get("DB_POOL_SIZE", 5))
    max_overflow = int(os.environ.get("DB_MAX_OVERFLOW", 10))
    engine = create_engine(url, pool_size=pool_size, max_overflow=max_overflow, echo=False)
    return engine


def get_engine_from_settings():
    load_dotenv()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL nu este setat. Adauga-l in fisierul .env, ex:\n"
            "DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/profu_db"
        )
    return get_engine(url)


# Instantiere globala Engine si Session
engine = get_engine_from_settings()

SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))

def get_session():
    """Returneaza o sesiune activa"""
    return SessionLocal()


def init_db():
    Base.metadata.create_all(engine)