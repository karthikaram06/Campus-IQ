# CampusIQ — Final Clean Build

A Django-based college management portal designed around a real-world workflow.

## Core workflow

- Student registration → Pending → Assigned class teacher approves → Student login enabled.
- Teacher registration → Pending → Admin approves → Teacher login enabled automatically.
- One classroom supports **Teacher One + Teacher Two**. Both assigned teachers can manage that class.
- Teacher attendance: enter **only absent register numbers**; everyone else is automatically Present.
- Teacher marks: update internal/external marks for every approved student in a class.
- Teacher achievements: add achievements from each student profile.
- Student: sees only their own dashboard, marks, attendance, timetable and leave.
- Student leave: submit and track approval/rejection.
- Admin: departments, teachers, classrooms, subjects, timetable, marks and other master data.
- AI Assistant: optional Gemini integration using an environment variable; the portal remains usable without AI.

## Setup on Windows

```bat
cd /d "C:\path\to\CampusIQ_Final_Clean\CampusIQ"
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

Admin: `http://127.0.0.1:8000/admin/`

## First admin setup

1. Create Department(s).
2. Approve teacher accounts in **Teacher Profiles**. Saving `APPROVED` automatically activates the linked login.
3. Create Classroom(s) and select Teacher One and Teacher Two from approved teacher profiles.
4. Create Subject(s).
5. Add timetable entries.
6. Students can now register by selecting their classroom.
7. Assigned teacher(s) approve pending students.
8. Teachers can take attendance and update marks.

## Gemini AI (optional)

Set your own key before starting the server:

```bat
set GEMINI_API_KEY=YOUR_KEY_HERE
python manage.py runserver
```

The key is read from the environment and is not stored in source code.
