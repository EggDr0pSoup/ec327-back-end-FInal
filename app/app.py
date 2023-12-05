import os
from typing import List, Optional
from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crawler import get_all_course_data, send_email_test
from app.db import Course, User, create_db_and_tables, get_async_session
from app.schemas import UserCreate, UserRead, UserUpdate, CourseRead
from app.users import auth_backend, current_active_user, fastapi_users
from fastapi.middleware.cors import CORSMiddleware

from fastapi_pagination import Page, add_pagination, paginate
from fastapi_pagination.utils import disable_installed_extensions_check
from apscheduler.schedulers.asyncio import AsyncIOScheduler

disable_installed_extensions_check()
load_dotenv()

app = FastAPI()
add_pagination(app)
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@app.get("/courses/", response_model=Page[CourseRead], tags=["courses"])
async def get_courses(session: AsyncSession = Depends(get_async_session)):
    async with session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()
        return paginate(courses)


@app.get("/courses/search-by-code/", response_model=Page[CourseRead], tags=["courses"])
async def search_courses_by_code(code: str, session: AsyncSession = Depends(get_async_session)):
    async with session:
        query = select(Course).filter(Course.code.ilike(f"%{code}%"))
        result = await session.execute(query)
        courses = result.scalars().all()
        return paginate(courses)


@app.get("/courses/search-by-name/", response_model=Page[CourseRead], tags=["courses"])
async def search_courses_by_name(name: str, session: AsyncSession = Depends(get_async_session)):
    async with session:
        query = select(Course).filter(Course.name.ilike(f"%{name}%"))
        result = await session.execute(query)
        courses = result.scalars().all()
        return paginate(courses)


@app.get("/courses/search-by-instructor/", response_model=Page[CourseRead], tags=["courses"])
async def search_courses_by_instructor(instructor: str, session: AsyncSession = Depends(get_async_session)):
    async with session:
        query = select(Course).filter(
            Course.instructor.ilike(f"%{instructor}%"))
        result = await session.execute(query)
        courses = result.scalars().all()
        return paginate(courses)


@app.post("/courses/enroll-course/{course_id}", tags=["courses"])
async def enroll_course(course_id: int, session: AsyncSession = Depends(get_async_session),
                        current_user: User = Depends(current_active_user)):
    user_id = current_user.id
    async with session:
        # Fetch the user and course
        user = await session.get(User, user_id)
        course = await session.get(Course, course_id)

        if not user or not course:
            return {"error": "User or course not found"}

        # Add the course to the user's courses if it's not already there
        if course not in user.courses:
            user.courses.append(course)
        await session.commit()

        return {"message": "Course added successfully"}


@app.post("/courses/drop-course/{course_id}", tags=["courses"])
async def drop_course(course_id: int, session: AsyncSession = Depends(get_async_session),
                      current_user: User = Depends(current_active_user)):
    user_id = current_user.id
    async with session:
        # Fetch the user and course
        user = await session.get(User, user_id)
        course = await session.get(Course, course_id)

        if not user or not course:
            return {"error": "User or course not found"}

        # Remove the course from the user's courses
        if course in user.courses:
            user.courses.remove(course)
            await session.commit()
            return {"message": "Course dropped successfully"}

        raise HTTPException(status_code=400, detail="Course not found")


@app.get("/courses/search/", response_model=Page[CourseRead])
async def search_courses(
    code: Optional[str] = None,
    name: Optional[str] = None,
    instructor: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    async with session:
        query = select(Course)

        # Add filters based on the provided query parameters
        conditions = []
        if code:
            conditions.append(Course.code.ilike(f"%{code}%"))
        if name:
            conditions.append(Course.name.ilike(f"%{name}%"))
        if instructor:
            conditions.append(Course.instructor.ilike(f"%{instructor}%"))

        if conditions:
            query = query.filter(or_(*conditions))

        result = await session.execute(query)
        courses = result.scalars().all()
        return paginate(courses)


@app.get("/courses/my-courses", response_model=List[CourseRead], tags=["courses"])
async def get_current_user_courses(current_user: User = Depends(current_active_user)):
    return current_user.courses


@app.get("/courses/my-available-courses", response_model=List[CourseRead], tags=["courses"])
async def get_current_user_courses_available(current_user: User = Depends(current_active_user)):
    available_courses = []
    for course in current_user.courses:
        if course.available > 0:
            available_courses.append(course)
    return available_courses


@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()
    if os.getenv('USE_CRAWLER', '0') == '1':
        scheduler = AsyncIOScheduler()
        scheduler.add_job(get_all_course_data, 'cron',
                          second='*/600')  # every 10 minutes
        scheduler.start()
    # scheduler = AsyncIOScheduler()
    # scheduler.add_job(send_email_test, 'cron',
    #                   second='*/5')  # every 5 seconds
    # scheduler.start()
