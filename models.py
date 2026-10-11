"""
SQLAlchemy data layer for the app: engine, session factory, and ORM models
for PostgreSQL (migrated from profu.db).
"""
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import Float, ForeignKey, Integer, String, Text, DateTime, create_engine, func, text, text
from sqlalchemy.engine import make_url
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
    # The one writing style every new conversation inherits, chosen on /account.
    # Plain Integer rather than a ForeignKey: deployed databases get this column
    # through _COLUMN_MIGRATIONS, which cannot add a constraint, so the value is
    # validated against the user's own styles when it is read.
    active_style_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

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


# =========================================================
# "ELEVII MEI" — classroom platform (students, profiling,
# smart groups). Ported from the raw-sqlite3 schema the
# feature was prototyped against onto the same SQLAlchemy
# layer the rest of the app uses.
# =========================================================


class Class(RowMixin, Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    students: Mapped[list["Student"]] = relationship(
        back_populates="school_class", cascade="all, delete-orphan"
    )
    groups: Mapped[list["Group"]] = relationship(
        back_populates="school_class", cascade="all, delete-orphan"
    )


class Student(RowMixin, Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    school_class: Mapped["Class"] = relationship(back_populates="students")
    metrics: Mapped[Optional["Metric"]] = relationship(
        back_populates="student", cascade="all, delete-orphan", uselist=False
    )
    profile: Mapped[Optional["Profile"]] = relationship(
        back_populates="student", cascade="all, delete-orphan", uselist=False
    )
    insight: Mapped[Optional["AiInsight"]] = relationship(
        back_populates="student", cascade="all, delete-orphan", uselist=False
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="student", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )
    test_records: Mapped[list["TestRecord"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    group_memberships: Mapped[list["GroupMember"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


class Metric(RowMixin, Base):
    __tablename__ = "metrics"

    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)
    attendance: Mapped[Optional[int]] = mapped_column(Integer)
    avg_grade: Mapped[Optional[float]] = mapped_column(Float)
    mastery_pct: Mapped[Optional[int]] = mapped_column(Integer)
    completion_pct: Mapped[Optional[int]] = mapped_column(Integer)
    avg_time_per_ex: Mapped[Optional[str]] = mapped_column(String)
    repeated_mistakes: Mapped[Optional[int]] = mapped_column(Integer)
    risk_level: Mapped[Optional[str]] = mapped_column(String)
    risk_trend: Mapped[Optional[str]] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    student: Mapped["Student"] = relationship(back_populates="metrics")


class Profile(RowMixin, Base):
    __tablename__ = "profiles"

    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)
    strengths: Mapped[Optional[str]] = mapped_column(Text)
    weaknesses: Mapped[Optional[str]] = mapped_column(Text)
    learning_style: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[Optional[str]] = mapped_column(String)
    risk_level: Mapped[Optional[str]] = mapped_column(String)
    personality_traits: Mapped[Optional[str]] = mapped_column(Text)
    attention_span: Mapped[Optional[str]] = mapped_column(Text)
    absent_lessons: Mapped[Optional[str]] = mapped_column(Text)

    student: Mapped["Student"] = relationship(back_populates="profile")


class AiInsight(RowMixin, Base):
    __tablename__ = "ai_insights"

    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)
    why_struggling: Mapped[Optional[str]] = mapped_column(Text)
    recommended_actions_json: Mapped[Optional[str]] = mapped_column(Text)

    student: Mapped["Student"] = relationship(back_populates="insight")


class ChatMessage(RowMixin, Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    student: Mapped["Student"] = relationship(back_populates="chat_messages")


class Group(RowMixin, Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    weakness_tag: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text)
    suggested_actions_json: Mapped[Optional[str]] = mapped_column(Text)

    school_class: Mapped["Class"] = relationship(back_populates="groups")
    members: Mapped[list["GroupMember"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class GroupMember(RowMixin, Base):
    __tablename__ = "group_members"

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)

    group: Mapped["Group"] = relationship(back_populates="members")
    student: Mapped["Student"] = relationship(back_populates="group_memberships")


class TestRecord(RowMixin, Base):
    __tablename__ = "test_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    grade: Mapped[Optional[float]] = mapped_column(Float)
    lessons: Mapped[Optional[str]] = mapped_column(Text)
    test_filename: Mapped[Optional[str]] = mapped_column(String)
    solution_filename: Mapped[Optional[str]] = mapped_column(String)
    ai_insights: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    # Minutes the student needed per exercise on this paper. Teacher-entered:
    # nothing in the app observes solving time, so it is the only real source
    # for the "timp/exercițiu" column on the risk overview.
    minutes_per_exercise: Mapped[Optional[float]] = mapped_column(Float)
    # JSON list of short error tags the AI review extracted from the solution
    # ("semne", "simplificare fracții", ...). Counting tags that show up on
    # more than one paper is what drives the "greșeli repetate" column.
    mistake_tags_json: Mapped[Optional[str]] = mapped_column(Text)
    # What the AI actually read off the uploaded pages, kept so the teacher can
    # check the transcription and so a re-analysis does not re-run OCR.
    transcript: Mapped[Optional[str]] = mapped_column(Text)

    student: Mapped["Student"] = relationship(back_populates="test_records")


# database_exists/create_database used to come from SQLAlchemy-Utils, which
# breaks on SQLAlchemy 2.1 (it subclasses the removed ScalarAttributeImpl).
# We only ever needed these two helpers, so they live here now and the app
# no longer pins SQLAlchemy to an old release.
def _admin_engine(url_obj):
    """Engine on the server's maintenance database, so we can inspect/create
    the app database itself. AUTOCOMMIT because CREATE DATABASE cannot run
    inside a transaction."""
    return create_engine(url_obj.set(database="postgres"), isolation_level="AUTOCOMMIT")


def database_exists(url):
    url_obj = make_url(url)
    if url_obj.get_backend_name() == "sqlite":
        name = url_obj.database
        return name in (None, "", ":memory:") or os.path.exists(name)

    engine = _admin_engine(url_obj)
    try:
        with engine.connect() as conn:
            found = conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url_obj.database},
            )
        return found is not None
    finally:
        engine.dispose()


def create_database(url):
    url_obj = make_url(url)
    if url_obj.get_backend_name() == "sqlite":
        return  # sqlite creates the file on first connect

    # CREATE DATABASE takes no bind parameters, so the name is quoted as an
    # identifier instead. It comes from DATABASE_URL, not from user input.
    name = url_obj.database.replace('"', '""')
    engine = _admin_engine(url_obj)
    try:
        with engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        engine.dispose()


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


# Columns added to tables that already exist in deployed databases.
# create_all() only ever CREATEs missing tables, so it will not widen a table
# that is already there - these run on every boot and are no-ops once applied.
_COLUMN_MIGRATIONS = [
    "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS minutes_per_exercise DOUBLE PRECISION",
    "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS mistake_tags_json TEXT",
    "ALTER TABLE test_records ADD COLUMN IF NOT EXISTS transcript TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS active_style_id INTEGER",
]


def init_db():
    Base.metadata.create_all(engine)

    with engine.begin() as connection:
        for statement in _COLUMN_MIGRATIONS:
            try:
                connection.execute(text(statement))
            except Exception as error:
                # A missing table is fine (create_all just made it with the
                # column already present); anything else is worth seeing.
                print(f"[migrations] skipped {statement!r}: {error}", flush=True)