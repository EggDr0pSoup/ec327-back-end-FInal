from typing import AsyncGenerator, List

from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Column, ForeignKey, Integer, String, Table, UniqueConstraint
DATABASE_URL = "sqlite+aiosqlite:///./course_scheduler.db"


class Base(DeclarativeBase):
    pass


# Association Table
user_course_association_table = Table(
    'user_course_association', Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('course_id', Integer, ForeignKey('course.id'))
)


class Course(Base):
    __tablename__ = "course"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    code: Mapped[str] = Column(String, index=True, nullable=False)
    name: Mapped[str] = Column(String, index=True, nullable=False)
    section: Mapped[str] = Column(String, index=True, nullable=False)
    instructor: Mapped[str] = Column(String, index=True)
    location: Mapped[str] = Column(String, index=True)
    schedule: Mapped[str] = Column(String, index=True)
    semester: Mapped[str] = Column(String, index=True, nullable=False)
    notes: Mapped[str] = Column(String)
    credits: Mapped[int] = Column(Integer)
    prerequisites: Mapped[str] = Column(String)
    available: Mapped[int] = Column(Integer)
    # Relationship to User
    users: Mapped[List['User']] = relationship(
        secondary=user_course_association_table, back_populates="courses",
        lazy='selectin')

    __table_args__ = (
        UniqueConstraint('code', 'section', 'semester',
                         name='_code_section_semester_uc'),
    )


class User(SQLAlchemyBaseUserTable[int], Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    courses: Mapped[List[Course]] = relationship(
        secondary=user_course_association_table, back_populates="users",
        lazy='selectin')


engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
