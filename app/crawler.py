import requests
import re
import random
from bs4 import BeautifulSoup
from sqlalchemy import select
from app.mail import EmailSchema, send_email
from app.db import Course, async_session_maker


async def insert_course_data(course_data):
    async with async_session_maker() as session:
        for course in course_data:
            course_query = await session.execute(
                select(Course).where(
                    Course.code == course['code'],
                    Course.section == course['section'],
                    Course.semester == course['semester']
                )
            )
            first_course = course_query.scalars().first()
            if not first_course:
                session.add(Course(**course))
            else:
                first_course.available = course['available']
                if course['available'] > 0:
                    for user in first_course.users:
                        email: EmailSchema = EmailSchema(
                            email=user.email,
                            subject='Course Available',
                            body=f'The course {course["code"]} {course["section"]} is available now!'
                        )
                        send_email(email)
        await session.commit()


def get_department_url_list():
    url = 'https://www.bu.edu/academics/'
    r = requests.get(url)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        url_list = [
            a.get('href')
            for a in soup.find_all('a', class_='button')
            if a.get('href') and a.get('href').startswith('/academics')
        ]
        return [f'https://www.bu.edu/academics{url}courses' for url in url_list]
    return []


def get_course_page_list_from_one_page(url):
    r = requests.get(url)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        course_page_url_list = [
            f'https://www.bu.edu{a.get("href")}'
            for a in soup.find('ul', class_='course-feed').find_all('a')
            if a.get('href') and a.get('href').startswith('/academics')
        ]
        return course_page_url_list
    return []


def get_course_page_list(url):
    total_course_page_list = []
    r = requests.get(url)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        page_url_base = ''
        for a in soup.find('div', class_='pagination').find_all('a'):
            match = re.findall(r'.*/courses/(\d+)', a.get('href'))
            page_max = 1
            page_min = 1
            if match:
                if int(match[0]) > page_max:
                    page_max = int(match[0])
                if int(match[0]) < page_min:
                    page_min = int(match[0])
                page_url_base = re.findall(
                    r'(.*/courses/)\d+', a.get('href'))[0]

        page_url_list = [f'{page_url_base}{page}' for page in range(
            page_min, page_max + 1)]
        for page_url in page_url_list:
            total_course_page_list.extend(
                get_course_page_list_from_one_page(page_url))
        return total_course_page_list
    return []


def get_course_info(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    # find div id=info-box
    info_box = soup.find("div", id="info-box")
    credits_tag = info_box.find('dt', string='Credits:')
    credits = credits_tag.find_next_sibling('dd').text if credits_tag else None

    # Extract prerequisites
    prerequisites_tag = info_box.find(
        'dt', string='Undergraduate Prerequisites:')
    prerequisites = prerequisites_tag.find_next_sibling(
        'dd').text if prerequisites_tag else None
    container = soup.find("div", class_="main")
    name = container.find("h1").text.strip()
    code = container.find("h2").text.strip()

    course_data = []
    for table in soup.find_all("table"):
        h4_tag = table.find_previous("h4")
        semester = h4_tag.text.strip() if h4_tag else "Unknown Semester"
        for row in table.find_all("tr")[1:]:
            columns = row.find_all("td")
            notes = columns[4].text.strip()
            available = 0
            if notes and "Full" not in notes:
                result = re.findall(r'\d+\s?/\s?(\d+)', notes)
                if result:
                    available = int(result[0])
            else:
                # To make the data more realistic, we assume that 5% of the courses
                # are available even if the notes say "Full".
                available = 1 if random.randint(1, 100) <= 5 else 0
            course_data.append({
                "section": columns[0].text.strip(),
                "instructor": columns[1].text.strip(),
                "location": columns[2].text.strip(),
                "schedule": columns[3].text.strip(),
                "code": code,
                "name": name,
                "notes": notes,
                "semester": semester,
                "credits": credits,
                "prerequisites": prerequisites,
                "available": available
            })
    return course_data


async def get_all_course_data():
    department_url_list = get_department_url_list()
    visited_department_url_list = []
    total_course_data = []
    for url in department_url_list:
        print(f'Getting course page list from {url}...')
        course_page_list = get_course_page_list(url)
        for url in course_page_list:
            if url in visited_department_url_list:
                continue
            print(f'Getting course data from {url}...')
            course_data = []
            try:
                course_data = get_course_info(url)
            except Exception as e:
                print(f'Error: {e}')
            total_course_data.extend(course_data)
            await insert_course_data(course_data)
            visited_department_url_list.append(url)
