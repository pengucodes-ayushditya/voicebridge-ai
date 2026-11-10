from contextlib import contextmanager
from threading import RLock

from sqlalchemy import JSON, Column, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings
from .schemas import Conversation

Base = declarative_base()
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)
Session = sessionmaker(bind=engine)
lock = RLock()


class Record(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True)
    payload = Column(JSON, nullable=False)


Base.metadata.create_all(engine)


class NotFound(ValueError):
    pass


class Conflict(ValueError):
    pass


def get(cid: str) -> Conversation:
    with Session() as session:
        record = session.get(Record, cid)
        if record is None:
            raise NotFound("Conversation not found")
        return Conversation.model_validate(record.payload)


def all_conversations() -> list[Conversation]:
    with Session() as session:
        return [
            Conversation.model_validate(r.payload) for r in session.query(Record).all()
        ]


def save(c: Conversation):
    with lock, Session.begin() as session:
        session.merge(Record(id=c.id, payload=c.model_dump(mode="json")))


@contextmanager
def edit(cid: str, version: int | None = None):
    with lock:
        c = get(cid)
        if version is not None and c.version != version:
            raise Conflict("This conversation changed. Reload before saving.")
        yield c
        c.version += 1
        save(c)


def delete(cid: str):
    with lock, Session.begin() as session:
        record = session.get(Record, cid)
        if record:
            session.delete(record)
