from typing import Optional
from fastapi_users import schemas
from pydantic import BaseModel


class CourseRead(BaseModel):
    id: int
    code: str
    name: str
    section: str
    instructor: Optional[str]
    location: Optional[str]
    schedule: Optional[str]
    semester: Optional[str]
    notes: Optional[str]
    credits: int
    prerequisites: Optional[str]
    available: int

    class Config:
        from_attributes = True


class UserRead(schemas.BaseUser[int]):
    courses: list[CourseRead] = []
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass
