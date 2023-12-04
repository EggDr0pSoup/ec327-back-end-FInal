import asyncio
from pydantic import EmailStr, BaseModel
from redmail import outlook

from dotenv import load_dotenv
import os

load_dotenv()


class EmailSchema(BaseModel):
    email: EmailStr
    subject: str
    body: str


def send_email(email: EmailSchema):
    outlook.username = os.getenv("MAIL_USERNAME")
    outlook.password = os.getenv("MAIL_PASSWORD")

    outlook.send(
        receivers=[email.email],
        subject=email.subject,
        text=email.body
    )


async def send_email_async(email_data: EmailSchema):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, send_email, email_data)
