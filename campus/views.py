import json
import time
import urllib.error
import urllib.request
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import (
    Achievement,
    Attendance,
    Classroom,
    Department,
    LeaveRequest,
    Mark,
    Project,
    StudentProfile,
    Subject,
    TeacherProfile,
    TimetableEntry,
)


# ============================================================
# HOME
# ============================================================

def home(request):
    return render(request, "campus/home.html")


# ============================================================
# PROFILE HELPERS
# ============================================================

def _teacher(request):
    try:
        return request.user.teacher_profile
    except TeacherProfile.DoesNotExist:
        return None


def _student(request):
    try:
        return request.user.student_profile
    except StudentProfile.DoesNotExist:
        return None


def _assigned_classrooms(teacher):
    return (
        Classroom.objects.filter(
            active=True,
            teacher_one=teacher,
        )
        | Classroom.objects.filter(
            active=True,
            teacher_two=teacher,
        )
    )


# ============================================================
# ROLE PROTECTION
# ============================================================

def teacher_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("teacher_login")

        teacher = _teacher(request)

        if (
            not teacher
            or teacher.status != "APPROVED"
            or not request.user.is_active
        ):
            messages.error(
                request,
                "Teacher account is not approved yet.",
            )
            return redirect("teacher_login")

        return view(request, *args, **kwargs)

    return wrapper


def student_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("student_login")

        student = _student(request)

        if (
            not student
            or student.status != "APPROVED"
            or not request.user.is_active
        ):
            messages.error(
                request,
                "Student account is not approved yet.",
            )
            return redirect("student_login")

        return view(request, *args, **kwargs)

    return wrapper


# ============================================================
# STUDENT REGISTRATION
# ============================================================

@require_http_methods(["GET", "POST"])
def student_register(request):

    classrooms = (
        Classroom.objects
        .filter(active=True)
        .select_related("department")
        .order_by("name")
    )

    if request.method == "POST":

        username = request.POST.get(
            "username",
            "",
        ).strip()

        password = request.POST.get(
            "password",
            "",
        )

        full_name = request.POST.get(
            "full_name",
            "",
        ).strip()

        email = request.POST.get(
            "email",
            "",
        ).strip()

        register_number = request.POST.get(
            "register_number",
            "",
        ).strip().upper()

        classroom_id = request.POST.get(
            "classroom",
        )

        college = request.POST.get(
            "college",
            "",
        ).strip()

        if not all([
            username,
            password,
            full_name,
            email,
            register_number,
            classroom_id,
        ]):
            messages.error(
                request,
                "Please complete all required fields.",
            )

        elif len(password) < 6:
            messages.error(
                request,
                "Password must contain at least 6 characters.",
            )

        elif User.objects.filter(
            username=username
        ).exists():
            messages.error(
                request,
                "Username already exists. Please choose another username.",
            )

        elif StudentProfile.objects.filter(
            register_number=register_number
        ).exists():
            messages.error(
                request,
                "Register number already exists.",
            )

        else:

            classroom = get_object_or_404(
                Classroom,
                pk=classroom_id,
                active=True,
            )

            with transaction.atomic():

                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=full_name,
                    email=email,
                    is_active=False,
                )

                StudentProfile.objects.create(
                    user=user,
                    register_number=register_number,
                    email=email,
                    college=college,
                    department=classroom.department,
                    classroom=classroom,
                    year=classroom.year,
                    section=classroom.section,
                )

            messages.success(
                request,
                "Account created successfully. "
                "Please wait for your class teacher to approve your account.",
            )

            return redirect("student_login")

    return render(
        request,
        "campus/register.html",
        {
            "role": "Student",
            "classrooms": classrooms,
        },
    )


# ============================================================
# TEACHER REGISTRATION
# ============================================================

@require_http_methods(["GET", "POST"])
def teacher_register(request):

    departments = Department.objects.all().order_by("name")

    if request.method == "POST":

        username = request.POST.get(
            "username",
            "",
        ).strip()

        password = request.POST.get(
            "password",
            "",
        )

        name = request.POST.get(
            "full_name",
            "",
        ).strip()

        email = request.POST.get(
            "email",
            "",
        ).strip()

        employee_id = request.POST.get(
            "employee_id",
            "",
        ).strip().upper()

        department_id = request.POST.get(
            "department",
        )

        designation = request.POST.get(
            "designation",
            "",
        ).strip()

        if not all([
            username,
            password,
            name,
            email,
            employee_id,
            department_id,
        ]):
            messages.error(
                request,
                "Please complete all required fields.",
            )

        elif len(password) < 6:
            messages.error(
                request,
                "Password must contain at least 6 characters.",
            )

        elif User.objects.filter(
            username=username
        ).exists():
            messages.error(
                request,
                "Username already exists. Please use another username.",
            )

        elif TeacherProfile.objects.filter(
            employee_id=employee_id
        ).exists():
            messages.error(
                request,
                "Employee ID already exists.",
            )

        else:

            department = get_object_or_404(
                Department,
                pk=department_id,
            )

            with transaction.atomic():

                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=name,
                    email=email,
                    is_active=False,
                )

                TeacherProfile.objects.create(
                    user=user,
                    employee_id=employee_id,
                    email=email,
                    department=department,
                    designation=designation,
                )

            messages.success(
                request,
                "Teacher account created. "
                "Admin approval is required before login.",
            )

            return redirect("teacher_login")

    return render(
        request,
        "campus/register.html",
        {
            "role": "Teacher",
            "departments": departments,
        },
    )


# ============================================================
# LOGIN
# ============================================================

def _login_for_role(request, role):

    if request.method == "POST":

        username = request.POST.get(
            "username",
            "",
        ).strip()

        password = request.POST.get(
            "password",
            "",
        )

        user = (
            User.objects
            .filter(username=username)
            .first()
        )

        if user:

            if (
                role == "Teacher"
                and hasattr(user, "teacher_profile")
            ):

                profile = user.teacher_profile

                if profile.status != "APPROVED":
                    messages.error(
                        request,
                        "Teacher account is waiting for admin approval.",
                    )
                    return None

            if (
                role == "Student"
                and hasattr(user, "student_profile")
            ):

                profile = user.student_profile

                if profile.status != "APPROVED":
                    messages.error(
                        request,
                        "Student account is waiting for teacher approval.",
                    )
                    return None

        authenticated = authenticate(
            request,
            username=username,
            password=password,
        )

        if authenticated:

            if (
                role == "Teacher"
                and hasattr(
                    authenticated,
                    "teacher_profile",
                )
                and authenticated.teacher_profile.status == "APPROVED"
                and authenticated.is_active
            ):

                login(
                    request,
                    authenticated,
                )

                return redirect(
                    "teacher_dashboard",
                )

            if (
                role == "Student"
                and hasattr(
                    authenticated,
                    "student_profile",
                )
                and authenticated.student_profile.status == "APPROVED"
                and authenticated.is_active
            ):

                login(
                    request,
                    authenticated,
                )

                return redirect(
                    "student_dashboard",
                )

        messages.error(
            request,
            "Invalid username or password.",
        )

    return None


@require_http_methods(["GET", "POST"])
def student_login(request):

    result = _login_for_role(
        request,
        "Student",
    )

    if result:
        return result

    return render(
        request,
        "campus/login.html",
        {
            "role": "Student",
        },
    )


@require_http_methods(["GET", "POST"])
def teacher_login(request):

    result = _login_for_role(
        request,
        "Teacher",
    )

    if result:
        return result

    return render(
        request,
        "campus/login.html",
        {
            "role": "Teacher",
        },
    )


# ============================================================
# LOGOUT
# ============================================================

def logout_view(request):
    logout(request)
    return redirect("home")


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@student_required
def student_dashboard(request):

    student = _student(request)

    marks = (
        student.marks
        .select_related("subject")
        .order_by("subject__code")
    )

    achievements = (
        student.achievements
        .order_by("-date", "-id")
    )

    projects = (
        student.projects
        .order_by("-created_at")
    )

    attendance = (
        Attendance.objects
        .filter(student=student)
        .select_related("subject")
    )

    return render(
        request,
        "campus/student_dashboard.html",
        {
            "student": student,
            "marks": marks,
            "achievements": achievements,
            "projects": projects,
            "attendance_pct": Attendance.percentage(student),
            "absent": attendance
                .filter(status="A")
                .order_by("-date")[:8],
            "pending_leaves": student
                .leave_requests
                .filter(status="PENDING")
                .count(),
        },
    )


# ============================================================
# STUDENT ATTENDANCE
# ============================================================

@student_required
def student_attendance(request):

    student = _student(request)

    subjects = (
        Subject.objects.filter(
            marks__student=student
        )
        |
        Subject.objects.filter(
            attendance_records__student=student
        )
    )

    subjects = (
        subjects
        .distinct()
        .order_by("code")
    )

    approved_leaves = LeaveRequest.objects.filter(
        student=student,
        status="APPROVED",
    )

    rows = []

    for subject in subjects:

        records = (
            Attendance.objects
            .filter(
                student=student,
                subject=subject,
            )
            .order_by("date")
        )

        approved_leave_dates = set()

        for leave in approved_leaves:

            current_date = leave.from_date

            while current_date <= leave.to_date:

                approved_leave_dates.add(current_date)

                from datetime import timedelta
                current_date += timedelta(days=1)

        daily_status = []
        record_dates = set()

        for record in records:

            record_dates.add(record.date)

            if record.status == "P":
                label = "Present"

            elif record.status == "A":
                label = "Absent"

            elif record.status == "L":
                label = "Leave"

            else:
                label = "Unknown"

            daily_status.append({
                "date": record.date,
                "status": record.status,
                "label": label,
            })

        # Approved leave always has priority.
        for leave_date in approved_leave_dates:

            found = False

            for item in daily_status:

                if item["date"] == leave_date:

                    item["status"] = "L"
                    item["label"] = "Leave"
                    found = True
                    break

            if not found:

                daily_status.append({
                    "date": leave_date,
                    "status": "L",
                    "label": "Leave",
                })

        daily_status.sort(
            key=lambda item: item["date"],
            reverse=True,
        )

        rows.append({
            "subject": subject,
            "percentage": Attendance.percentage(
                student,
                subject,
            ),
            "absent": records
                .filter(status="A")
                .order_by("-date"),
            "leave_dates": sorted(
                approved_leave_dates,
                reverse=True,
            ),
            "records": daily_status,
            "total": records
                .exclude(status="L")
                .count(),
        })

    return render(
        request,
        "campus/student_attendance.html",
        {
            "rows": rows,
            "overall": Attendance.percentage(student),
        },
    )


# ============================================================
# STUDENT TIMETABLE
# ============================================================

@student_required
def student_timetable(request):

    student = _student(request)

    days = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
    ]

    periods = list(range(1, 9))

    if student.classroom:

        entries = (
            TimetableEntry.objects
            .filter(
                classroom=student.classroom,
                day__in=[
                    "MON",
                    "TUE",
                    "WED",
                    "THU",
                    "FRI",
                ],
                period__in=periods,
            )
            .select_related("subject")
            .order_by(
                "period",
                "day",
            )
        )

    else:

        entries = TimetableEntry.objects.none()

    grid = {
        (
            entry.day,
            entry.period,
        ): entry

        for entry in entries
    }

    period_times = {}

    for period in periods:

        period_time = ""

        for entry in entries:

            if (
                entry.period == period
                and entry.time
            ):

                period_time = entry.time
                break

        period_times[period] = period_time

    return render(
        request,
        "campus/timetable.html",
        {
            "days": days,
            "periods": periods,
            "grid": grid,
            "period_times": period_times,
            "classroom": student.classroom,
        },
    )


# ============================================================
# TEACHER TIMETABLE EDITOR
# ============================================================

@teacher_required
@require_http_methods(["GET", "POST"])
def teacher_timetable(
    request,
    classroom_id,
):

    teacher = _teacher(request)

    classroom = get_object_or_404(
        _assigned_classrooms(teacher),
        pk=classroom_id,
        active=True,
    )

    days = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
    ]

    periods = list(range(1, 9))

    if teacher.department:

        subjects = (
            Subject.objects
            .filter(
                department=teacher.department,
            )
            .order_by(
                "semester",
                "code",
            )
        )

    else:

        subjects = Subject.objects.none()

    if request.method == "POST":

        period_times = {}

        for period in periods:

            period_times[period] = request.POST.get(
                f"time_{period}",
                "",
            ).strip()

        subject_map = {
            str(subject.id): subject
            for subject in subjects
        }

        changes = []

        for day_code, day_name in days:

            for period in periods:

                subject_id = request.POST.get(
                    f"subject_{day_code}_{period}",
                    "",
                ).strip()

                subject = None

                if subject_id:

                    subject = subject_map.get(
                        subject_id,
                    )

                    if subject is None:

                        messages.error(
                            request,
                            "Invalid subject selected.",
                        )

                        return redirect(
                            "teacher_timetable",
                            classroom_id=classroom.id,
                        )

                custom_subject = request.POST.get(
                    f"custom_{day_code}_{period}",
                    "",
                ).strip()

                faculty = request.POST.get(
                    f"faculty_{day_code}_{period}",
                    "",
                ).strip()

                room = request.POST.get(
                    f"room_{day_code}_{period}",
                    "",
                ).strip()

                time_value = period_times.get(
                    period,
                    "",
                ).strip()

                if not time_value:
                    time_value = f"Period {period}"

                changes.append({
                    "day": day_code,
                    "period": period,
                    "subject": subject,
                    "custom_subject": custom_subject,
                    "faculty": faculty,
                    "room": room,
                    "time": time_value,
                })

        with transaction.atomic():

            for change in changes:

                TimetableEntry.objects.update_or_create(
                    classroom=classroom,
                    day=change["day"],
                    period=change["period"],
                    defaults={
                        "time": change["time"],
                        "subject": change["subject"],
                        "custom_subject": change["custom_subject"],
                        "faculty": change["faculty"],
                        "room": change["room"],
                    },
                )

        messages.success(
            request,
            "Timetable updated successfully.",
        )

        return redirect(
            "teacher_timetable",
            classroom_id=classroom.id,
        )

    entries = (
        TimetableEntry.objects
        .filter(
            classroom=classroom,
            day__in=[
                "MON",
                "TUE",
                "WED",
                "THU",
                "FRI",
            ],
            period__in=periods,
        )
        .select_related("subject")
        .order_by(
            "day",
            "period",
        )
    )

    grid = {
        (
            entry.day,
            entry.period,
        ): entry

        for entry in entries
    }

    period_times = {}

    for period in periods:

        period_time = ""

        for entry in entries:

            if (
                entry.period == period
                and entry.time
            ):

                period_time = entry.time
                break

        period_times[period] = period_time

    return render(
        request,
        "campus/teacher_timetable.html",
        {
            "teacher": teacher,
            "classroom": classroom,
            "days": days,
            "periods": periods,
            "subjects": subjects,
            "grid": grid,
            "period_times": period_times,
        },
    )


# ============================================================
# STUDENT LEAVE
# ============================================================

@student_required
@require_http_methods(["GET", "POST"])
def student_leave(request):

    student = _student(request)

    if request.method == "POST":

        leave_date = request.POST.get(
            "leave_date",
            "",
        ).strip()

        reason = request.POST.get(
            "reason",
            "",
        ).strip()

        description = request.POST.get(
            "description",
            "",
        ).strip()

        if not leave_date:

            messages.error(
                request,
                "Please select the leave date.",
            )

        elif not reason:

            messages.error(
                request,
                "Please enter the reason for leave.",
            )

        else:

            try:
                selected_date = date.fromisoformat(
                    leave_date,
                )

            except ValueError:

                messages.error(
                    request,
                    "Please select a valid date.",
                )

            else:

                duplicate = (
                    LeaveRequest.objects
                    .filter(
                        student=student,
                        from_date=selected_date,
                        to_date=selected_date,
                    )
                    .exists()
                )

                if duplicate:

                    messages.warning(
                        request,
                        "You have already submitted a leave request for this date.",
                    )

                else:

                    # Existing database uses from_date/to_date.
                    # For the new one-day leave system,
                    # both fields contain the same date.
                    LeaveRequest.objects.create(
                        student=student,
                        from_date=selected_date,
                        to_date=selected_date,
                        reason=reason,
                        description=description,
                    )

                    messages.success(
                        request,
                        "Leave request submitted successfully.",
                    )

                    return redirect(
                        "student_leave",
                    )

    leaves = (
        student.leave_requests
        .order_by("-created_at")
    )

    return render(
        request,
        "campus/leave.html",
        {
            "student": student,
            "leaves": leaves,
        },
    )


# ============================================================
# TEACHER DASHBOARD
# ============================================================

@teacher_required
def teacher_dashboard(request):

    teacher = _teacher(request)

    classrooms = (
        _assigned_classrooms(teacher)
        .distinct()
        .order_by("name")
    )

    pending = (
        StudentProfile.objects
        .filter(
            classroom__in=classrooms,
            status="PENDING",
        )
        .select_related(
            "user",
            "classroom",
        )
    )

    students = (
        StudentProfile.objects
        .filter(
            classroom__in=classrooms,
            status="APPROVED",
        )
        .select_related(
            "user",
            "classroom",
        )
        .order_by(
            "classroom__name",
            "register_number",
        )
    )

    subjects = (
        Subject.objects
        .filter(
            department=teacher.department,
        )
        .order_by(
            "semester",
            "code",
        )
        if teacher.department
        else Subject.objects.none()
    )

    leaves = (
        LeaveRequest.objects
        .filter(
            student__classroom__in=classrooms,
            status="PENDING",
        )
        .select_related(
            "student__user",
            "student__classroom",
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "campus/teacher_dashboard.html",
        {
            "teacher": teacher,
            "classrooms": classrooms,
            "pending": pending,
            "students": students,
            "subjects": subjects,
            "leaves": leaves,
            "student_count": students.count(),
            "pending_count": pending.count(),
            "leave_count": leaves.count(),
        },
    )


# ============================================================
# TEACHER - STUDENT DETAIL
# ============================================================

@teacher_required
@require_http_methods(["GET", "POST"])
def teacher_student_detail(
    request,
    student_id,
):
    """Complete teacher-side student management workspace."""

    teacher = _teacher(request)

    student = get_object_or_404(
        StudentProfile.objects.select_related(
            "user",
            "department",
            "classroom",
        ),
        pk=student_id,
        classroom__in=_assigned_classrooms(teacher),
        status="APPROVED",
    )

    assigned_classrooms = _assigned_classrooms(teacher).select_related("department").order_by("name")

    subjects = (
        Subject.objects
        .filter(
            department=student.department,
        )
        .order_by("semester", "code")
    ) if student.department else Subject.objects.none()

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        # --------------------------------------------------------
        # ACCOUNT / PROFILE UPDATE
        # --------------------------------------------------------
        if action == "update_profile":
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            username = request.POST.get("username", "").strip()
            email = request.POST.get("email", "").strip()
            phone = request.POST.get("phone", "").strip()
            college = request.POST.get("college", "").strip()
            classroom_id = request.POST.get("classroom_id", "").strip()
            register_number = request.POST.get("register_number", "").strip().upper()
            year = request.POST.get("year", "").strip()
            section = request.POST.get("section", "").strip().upper()
            cgpa_raw = request.POST.get("cgpa", "0").strip()
            new_password = request.POST.get("new_password", "")
            is_active = request.POST.get("account_active") == "on"

            if not first_name:
                messages.error(request, "First name is required.")
                return redirect("teacher_student_detail", student_id=student.id)

            if not username:
                messages.error(request, "Username is required.")
                return redirect("teacher_student_detail", student_id=student.id)

            username_exists = (
                User.objects
                .filter(username=username)
                .exclude(pk=student.user_id)
                .exists()
            )
            if username_exists:
                messages.error(request, "That username is already in use.")
                return redirect("teacher_student_detail", student_id=student.id)

            register_exists = (
                StudentProfile.objects
                .filter(register_number=register_number)
                .exclude(pk=student.id)
                .exists()
            )
            if register_exists:
                messages.error(request, "That register number is already in use.")
                return redirect("teacher_student_detail", student_id=student.id)

            try:
                cgpa = Decimal(cgpa_raw or "0")
            except (InvalidOperation, ValueError):
                cgpa = Decimal("-1")

            if not Decimal("0") <= cgpa <= Decimal("10"):

                messages.error(request, "CGPA must be between 0 and 10.")
                return redirect("teacher_student_detail", student_id=student.id)

            student.user.first_name = first_name
            student.user.last_name = last_name
            student.user.username = username
            student.user.email = email
            student.user.is_active = is_active
            student.user.save(
                update_fields=[
                    "first_name",
                    "last_name",
                    "username",
                    "email",
                    "is_active",
                ]
            )

            assigned_classrooms = _assigned_classrooms(teacher)
            new_classroom = get_object_or_404(assigned_classrooms, pk=classroom_id)

            student.email = email
            student.phone = phone
            student.college = college
            student.classroom = new_classroom
            student.department = new_classroom.department
            student.register_number = register_number
            student.year = year
            student.section = section
            student.cgpa = cgpa
            student.save(
                update_fields=[
                    "email",
                    "phone",
                    "college",
                    "classroom",
                    "department",
                    "register_number",
                    "year",
                    "section",
                    "cgpa",
                ]
            )

            if new_password.strip():
                if len(new_password) < 8:
                    messages.error(request, "New password must be at least 8 characters.")
                    return redirect("teacher_student_detail", student_id=student.id)
                student.user.set_password(new_password)
                student.user.save(update_fields=["password"])
                messages.success(
                    request,
                    "Student profile updated and account password changed successfully.",
                )
            else:
                messages.success(request, "Student profile and account updated successfully.")

            return redirect("teacher_student_detail", student_id=student.id)

        # --------------------------------------------------------
        # MARK UPDATE / DELETE
        # --------------------------------------------------------
        if action == "save_mark":
            mark_id = request.POST.get("mark_id", "").strip()
            subject_id = request.POST.get("subject_id", "").strip()
            internal_raw = request.POST.get("internal", "0").strip()
            external_raw = request.POST.get("external", "0").strip()

            subject = get_object_or_404(
                Subject,
                pk=subject_id,
                department=student.department,
            )

            try:
                internal = int(internal_raw or 0)
                external = int(external_raw or 0)
            except ValueError:
                messages.error(request, "Internal and external marks must be numbers.")
                return redirect("teacher_student_detail", student_id=student.id)

            if not (0 <= internal <= 50 and 0 <= external <= 50):
                messages.error(request, "Marks must be between 0 and 50.")
                return redirect("teacher_student_detail", student_id=student.id)

            mark = None
            if mark_id:
                mark = get_object_or_404(
                    Mark,
                    pk=mark_id,
                    student=student,
                )
                if mark.subject_id != subject.id:
                    messages.error(request, "Invalid subject for this mark record.")
                    return redirect("teacher_student_detail", student_id=student.id)

            Mark.objects.update_or_create(
                student=student,
                subject=subject,
                defaults={
                    "internal": internal,
                    "external": external,
                },
            )
            messages.success(request, f"{subject.code} marks saved successfully.")
            return redirect("teacher_student_detail", student_id=student.id)

        if action == "delete_mark":
            mark = get_object_or_404(Mark, pk=request.POST.get("mark_id"), student=student)
            code = mark.subject.code
            mark.delete()
            messages.success(request, f"{code} mark record deleted.")
            return redirect("teacher_student_detail", student_id=student.id)

        # --------------------------------------------------------
        # ATTENDANCE UPDATE / DELETE
        # --------------------------------------------------------
        if action == "save_attendance":
            attendance_id = request.POST.get("attendance_id", "").strip()
            subject_id = request.POST.get("attendance_subject_id", "").strip()
            attendance_date = request.POST.get("attendance_date", "").strip()
            status = request.POST.get("attendance_status", "P").strip().upper()

            if status not in {"P", "A", "L"}:
                messages.error(request, "Invalid attendance status.")
                return redirect("teacher_student_detail", student_id=student.id)

            try:
                selected_date = date.fromisoformat(attendance_date)
            except ValueError:
                messages.error(request, "Invalid attendance date.")
                return redirect("teacher_student_detail", student_id=student.id)

            if selected_date.weekday() == 6:
                messages.error(request, "Sunday is a weekly holiday and cannot be recorded as attendance.")
                return redirect("teacher_student_detail", student_id=student.id)

            subject = get_object_or_404(
                Subject,
                pk=subject_id,
                department=student.department,
            )

            existing = Attendance.objects.filter(
                student=student,
                subject=subject,
                date=selected_date,
            ).first()

            if attendance_id:
                existing_by_id = get_object_or_404(
                    Attendance,
                    pk=attendance_id,
                    student=student,
                )
                if existing_by_id.pk != getattr(existing, "pk", None):
                    messages.error(request, "Another attendance record already exists for that student, subject and date.")
                    return redirect("teacher_student_detail", student_id=student.id)
                existing = existing_by_id

            Attendance.objects.update_or_create(
                student=student,
                subject=subject,
                date=selected_date,
                defaults={
                    "status": status,
                    "teacher": teacher,
                },
            )
            messages.success(request, "Attendance record saved successfully.")
            return redirect("teacher_student_detail", student_id=student.id)

        if action == "delete_attendance":
            attendance = get_object_or_404(
                Attendance,
                pk=request.POST.get("attendance_id"),
                student=student,
            )
            attendance.delete()
            messages.success(request, "Attendance record deleted.")
            return redirect("teacher_student_detail", student_id=student.id)

        # --------------------------------------------------------
        # ACHIEVEMENT ADD / UPDATE / DELETE
        # --------------------------------------------------------
        if action == "save_achievement":
            achievement_id = request.POST.get("achievement_id", "").strip()
            title = request.POST.get("achievement_title", "").strip()
            issuer = request.POST.get("achievement_issuer", "").strip()
            achievement_date = request.POST.get("achievement_date", "").strip() or None
            description = request.POST.get("achievement_description", "").strip()

            if not title:
                messages.error(request, "Achievement title is required.")
                return redirect("teacher_student_detail", student_id=student.id)

            if achievement_id:
                achievement = get_object_or_404(
                    Achievement,
                    pk=achievement_id,
                    student=student,
                )
                achievement.title = title
                achievement.issuer = issuer
                achievement.date = achievement_date
                achievement.description = description
                achievement.save()
                messages.success(request, "Achievement updated successfully.")
            else:
                Achievement.objects.create(
                    student=student,
                    title=title,
                    issuer=issuer,
                    date=achievement_date,
                    description=description,
                )
                messages.success(request, "Achievement added successfully.")

            return redirect("teacher_student_detail", student_id=student.id)

        if action == "delete_achievement":
            achievement = get_object_or_404(
                Achievement,
                pk=request.POST.get("achievement_id"),
                student=student,
            )
            achievement.delete()
            messages.success(request, "Achievement deleted.")
            return redirect("teacher_student_detail", student_id=student.id)

        # --------------------------------------------------------
        # PROJECT ADD / UPDATE / DELETE
        # --------------------------------------------------------
        if action == "save_project":
            project_id = request.POST.get("project_id", "").strip()
            title = request.POST.get("project_title", "").strip()
            description = request.POST.get("project_description", "").strip()
            tech_stack = request.POST.get("project_tech_stack", "").strip()
            link = request.POST.get("project_link", "").strip()
            project_status = request.POST.get("project_status", "In Progress").strip() or "In Progress"

            if not title:
                messages.error(request, "Project title is required.")
                return redirect("teacher_student_detail", student_id=student.id)

            if project_id:
                project = get_object_or_404(
                    Project,
                    pk=project_id,
                    student=student,
                )
                project.title = title
                project.description = description
                project.tech_stack = tech_stack
                project.link = link
                project.status = project_status
                project.save()
                messages.success(request, "Project updated successfully.")
            else:
                Project.objects.create(
                    student=student,
                    title=title,
                    description=description,
                    tech_stack=tech_stack,
                    link=link,
                    status=project_status,
                )
                messages.success(request, "Project added successfully.")

            return redirect("teacher_student_detail", student_id=student.id)

        if action == "delete_project":
            project = get_object_or_404(
                Project,
                pk=request.POST.get("project_id"),
                student=student,
            )
            project.delete()
            messages.success(request, "Project deleted.")
            return redirect("teacher_student_detail", student_id=student.id)

        messages.error(request, "Unknown student management action.")
        return redirect("teacher_student_detail", student_id=student.id)

    marks = (
        Mark.objects
        .filter(student=student)
        .select_related("subject")
        .order_by("subject__semester", "subject__code")
    )

    attendance = (
        Attendance.objects
        .filter(student=student)
        .select_related("subject")
        .order_by("-date", "subject__code")
    )

    achievements = student.achievements.order_by("-date", "-id")
    projects = student.projects.order_by("-created_at")

    absent_days = (
        Attendance.objects
        .filter(student=student, status="A")
        .exclude(date__week_day=1)
        .values("date")
        .distinct()
        .count()
    )

    return render(
        request,
        "campus/teacher_student.html",
        {
            "teacher": teacher,
            "assigned_classrooms": assigned_classrooms,
            "student": student,
            "subjects": subjects,
            "marks": marks,
            "attendance": attendance,
            "achievements": achievements,
            "projects": projects,
            "absent_days": absent_days,
            "account_active": student.user.is_active,
        },
    )


# ============================================================
# TEACHER - VERIFY STUDENT
# ============================================================

@teacher_required
@require_http_methods(["POST"])
def teacher_verify_student(
    request,
    student_id,
    action,
):

    teacher = _teacher(request)

    student = get_object_or_404(
        StudentProfile,
        pk=student_id,
        classroom__in=_assigned_classrooms(teacher),
        status="PENDING",
    )

    if action not in {
        "approve",
        "reject",
    }:

        messages.error(
            request,
            "Invalid verification action.",
        )

        return redirect(
            "teacher_dashboard",
        )

    if action == "approve":

        student.status = "APPROVED"
        student.user.is_active = True

        message = (
            f"Student {student.register_number} "
            "has been approved."
        )

    else:

        student.status = "REJECTED"
        student.user.is_active = False

        message = (
            f"Student {student.register_number} "
            "has been rejected."
        )

    student.user.save(
        update_fields=["is_active"],
    )

    student.save(
        update_fields=["status"],
    )

    messages.success(
        request,
        message,
    )

    return redirect(
        "teacher_dashboard",
    )


# ============================================================
# TEACHER ATTENDANCE
# ============================================================

@teacher_required
@require_http_methods(["GET", "POST"])
def teacher_attendance(
    request,
    classroom_id,
    subject_id,
):

    teacher = _teacher(request)

    classroom = get_object_or_404(
        _assigned_classrooms(teacher),
        pk=classroom_id,
    )

    subject = get_object_or_404(
        Subject,
        pk=subject_id,
        department=teacher.department,
    )

    students = (
        StudentProfile.objects
        .filter(
            classroom=classroom,
            status="APPROVED",
        )
        .order_by("register_number")
    )

    selected = request.GET.get(
        "date",
        date.today().isoformat(),
    ).strip()

    if request.method == "POST":

        selected = request.POST.get(
            "date",
            date.today().isoformat(),
        ).strip()

        try:

            selected_date = date.fromisoformat(
                selected,
            )

        except ValueError:

            messages.error(
                request,
                "Invalid attendance date.",
            )

            return redirect(
                "teacher_attendance",
                classroom_id=classroom.id,
                subject_id=subject.id,
            )

        # Only absent register numbers are entered.
        absent = {
            value.strip().upper()
            for value in request.POST.get(
                "absent_registers",
                "",
            )
            .replace(",", " ")
            .split()
            if value.strip()
        }

        valid_registers = set(
            students.values_list(
                "register_number",
                flat=True,
            )
        )

        unknown = absent - valid_registers

        absent &= valid_registers

        leave_count = 0

        for student in students:

            has_approved_leave = (
                LeaveRequest.objects
                .filter(
                    student=student,
                    status="APPROVED",
                    from_date__lte=selected_date,
                    to_date__gte=selected_date,
                )
                .exists()
            )

            # Approved leave has highest priority.
            if has_approved_leave:

                attendance_status = "L"
                leave_count += 1

            elif student.register_number in absent:

                attendance_status = "A"

            else:

                attendance_status = "P"

            Attendance.objects.update_or_create(
                student=student,
                subject=subject,
                date=selected_date,
                defaults={
                    "status": attendance_status,
                    "teacher": teacher,
                },
            )

        message = (
            "Attendance saved successfully. "
            f"{len(absent)} absent, "
            f"{leave_count} on approved leave, "
            "everyone else is Present."
        )

        if unknown:

            message += (
                " Unknown register numbers ignored: "
                + ", ".join(
                    sorted(unknown)
                )
                + "."
            )

        messages.success(
            request,
            message,
        )

        return redirect(
            "teacher_attendance",
            classroom_id=classroom.id,
            subject_id=subject.id,
        )

    # Existing attendance for selected date.
    existing = {
        attendance.student_id:
            attendance.status
        for attendance in Attendance.objects.filter(
            subject=subject,
            date=selected,
        )
    }

    # Students having approved leave on selected date.
    approved_leave_students = set(
        LeaveRequest.objects
        .filter(
            student__in=students,
            status="APPROVED",
            from_date__lte=selected,
            to_date__gte=selected,
        )
        .values_list(
            "student_id",
            flat=True,
        )
    )

    # Show existing absent register numbers,
    # excluding students who are on approved leave.
    absent_registers = " ".join(
        student.register_number
        for student in students
        if (
            existing.get(student.id) == "A"
            and student.id not in approved_leave_students
        )
    )

    return render(
        request,
        "campus/attendance_form.html",
        {
            "classroom": classroom,
            "subject": subject,
            "students": students,
            "selected_date": selected,
            "existing": existing,
            "approved_leave_students":
                approved_leave_students,
            "absent_registers":
                absent_registers,
        },
    )


# ============================================================
# TEACHER MARKS
# ============================================================

@teacher_required
@require_http_methods(["GET", "POST"])
def teacher_marks(
    request,
    classroom_id,
    subject_id,
):

    teacher = _teacher(request)

    classroom = get_object_or_404(
        _assigned_classrooms(teacher),
        pk=classroom_id,
    )

    subject = get_object_or_404(
        Subject,
        pk=subject_id,
        department=teacher.department,
    )

    students = (
        StudentProfile.objects
        .filter(
            classroom=classroom,
            status="APPROVED",
        )
        .order_by("register_number")
        .select_related("user")
    )

    current = {
        mark.student_id: mark
        for mark in Mark.objects.filter(
            student__in=students,
            subject=subject,
        )
    }

    if request.method == "POST":

        errors = []

        for student in students:

            try:

                internal = int(
                    request.POST.get(
                        f"internal_{student.id}",
                        0,
                    )
                )

                external = int(
                    request.POST.get(
                        f"external_{student.id}",
                        0,
                    )
                )

                if not (
                    0 <= internal <= 50
                    and
                    0 <= external <= 50
                ):
                    raise ValueError

                Mark.objects.update_or_create(
                    student=student,
                    subject=subject,
                    defaults={
                        "internal": internal,
                        "external": external,
                    },
                )

            except (
                TypeError,
                ValueError,
            ):

                errors.append(
                    student.register_number
                )

        if errors:

            messages.error(
                request,
                "Marks must be between 0 and 50. "
                "Check: "
                + ", ".join(errors),
            )

        else:

            messages.success(
                request,
                f"{subject.code} marks updated successfully.",
            )

            return redirect(
                "teacher_marks",
                classroom_id=classroom.id,
                subject_id=subject.id,
            )

        current = {
            mark.student_id: mark
            for mark in Mark.objects.filter(
                student__in=students,
                subject=subject,
            )
        }

    return render(
        request,
        "campus/teacher_marks.html",
        {
            "classroom": classroom,
            "subject": subject,
            "students": students,
            "current": current,
        },
    )


# ============================================================
# TEACHER - ACHIEVEMENT
# ============================================================

@teacher_required
@require_http_methods(["GET", "POST"])
def teacher_add_achievement(
    request,
    student_id,
):

    teacher = _teacher(request)

    student = get_object_or_404(
        StudentProfile,
        pk=student_id,
        classroom__in=_assigned_classrooms(teacher),
        status="APPROVED",
    )

    if request.method == "POST":

        title = request.POST.get(
            "title",
            "",
        ).strip()

        if not title:

            messages.error(
                request,
                "Achievement title is required.",
            )

        else:

            Achievement.objects.create(
                student=student,
                title=title,
                issuer=request.POST.get(
                    "issuer",
                    "",
                ).strip(),
                date=request.POST.get(
                    "date",
                ) or None,
                description=request.POST.get(
                    "description",
                    "",
                ).strip(),
            )

            messages.success(
                request,
                "Achievement added successfully.",
            )

            return redirect(
                "teacher_student_detail",
                student_id=student.id,
            )

    return render(
        request,
        "campus/achievement_form.html",
        {
            "student": student,
        },
    )


# ============================================================
# TEACHER - LEAVE APPROVE / REJECT
# ============================================================

@teacher_required
@require_http_methods(["POST"])
def teacher_leave_action(
    request,
    leave_id,
    action,
):

    teacher = _teacher(request)

    leave = get_object_or_404(
        LeaveRequest,
        pk=leave_id,
        student__classroom__in=_assigned_classrooms(
            teacher,
        ),
    )

    if action not in {
        "approve",
        "reject",
    }:

        messages.error(
            request,
            "Invalid leave action.",
        )

    else:

        if action == "approve":

            leave.status = "APPROVED"

            # If attendance was already taken for this date,
            # change it to Leave automatically.
            Attendance.objects.filter(
                student=leave.student,
                date__gte=leave.from_date,
                date__lte=leave.to_date,
            ).update(
                status="L",
                teacher=teacher,
            )

        else:

            leave.status = "REJECTED"

        leave.reviewed_by = teacher

        leave.save(
            update_fields=[
                "status",
                "reviewed_by",
            ]
        )

        messages.success(
            request,
            f"Leave request {leave.status.lower()}.",
        )

    return redirect(
        "teacher_dashboard",
    )


# ============================================================
# ============================================================
# OPENROUTER AI
# ============================================================

def _openrouter(prompt):

    api_key = getattr(settings, "OPENROUTER_API_KEY", "").strip()
    model = getattr(
        settings,
        "OPENROUTER_MODEL",
        "openrouter/free",
    ).strip()

    if not api_key:
        return (
            "OpenRouter API key is not configured. "
            "Please set OPENROUTER_API_KEY and restart the server."
        )

    url = "https://openrouter.ai/api/v1/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }).encode("utf-8")

    max_attempts = 4

    for attempt in range(max_attempts):

        request_object = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "http://127.0.0.1:8000",
                "X-Title": "CampusIQ AI",
            },
            method="POST",
        )

        try:

            with urllib.request.urlopen(
                request_object,
                timeout=60,
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

            choices = data.get("choices", [])

            if not choices:
                return (
                    "OpenRouter did not return an answer. "
                    "Please try again."
                )

            message = choices[0].get("message", {})
            answer = message.get("content", "")

            if isinstance(answer, list):
                answer = "".join(
                    part.get("text", "")
                    for part in answer
                    if isinstance(part, dict)
                    and part.get("text")
                )

            answer = str(answer).strip()

            return (
                answer
                if answer
                else
                "OpenRouter returned an empty response. "
                "Please try again."
            )

        except urllib.error.HTTPError as error:

            try:
                error_body = error.read().decode("utf-8")
            except Exception:
                error_body = ""

            if (
                error.code in (408, 429, 500, 502, 503, 504)
                and attempt < max_attempts - 1
            ):
                time.sleep(2 ** attempt)
                continue

            if error.code == 401:
                return (
                    "OpenRouter API authentication failed. "
                    "Please check your API key."
                )

            if error.code == 402:
                return (
                    "OpenRouter returned 402. The selected model/provider "
                    "may require credits. Please choose a free model."
                )

            if error.code == 429:
                return (
                    "OpenRouter rate limit was reached. "
                    "Please wait a moment and try again."
                )

            if error.code in (500, 502, 503, 504):
                return (
                    "OpenRouter is temporarily unavailable. "
                    "Please try again in a moment."
                )

            return (
                f"OpenRouter API error ({error.code}). "
                f"{error_body[:500]}"
            )

        except Exception as error:

            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)
                continue

            return (
                "OpenRouter connection error: "
                f"{error}"
            )

    return (
        "OpenRouter is temporarily unavailable. "
        "Please try again."
    )


# ============================================================
# AI ASSISTANT
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def ai_assistant(request):

    answer = None

    if request.method == "POST":

        question = request.POST.get(
            "question",
            "",
        ).strip()

        mode = request.POST.get(
            "mode",
            "general",
        )

        if not question:

            messages.error(
                request,
                "Type a question first.",
            )

        else:

            # ------------------------------------------------
            # CAMPUSIQ AI RESPONSE STYLE
            # ------------------------------------------------

            base_instruction = """
You are CampusIQ AI, a friendly and practical academic
assistant designed for college students.

IMPORTANT RESPONSE RULES:

1. Give the direct answer first.
2. Use simple and easy-to-understand English.
3. Avoid unnecessary long paragraphs.
4. Use clear headings for different topics.
5. Make headings and important topics bold.
6. Use bullet points whenever possible.
7. Use numbered steps for procedures or roadmaps.
8. Give practical examples when useful.
9. If the question asks "how to", explain step-by-step.
10. If the question is about coding, provide clean code
    and explain the important parts briefly.
11. If the question is about interviews, provide sample
    answers that a student can actually say.
12. If the question is about placements, give a practical
    preparation plan.
13. If the question is about projects, suggest realistic
    technologies, features and implementation steps.
14. If the question is about career planning, give a
    realistic roadmap.
15. Do not repeat the user's question unnecessarily.
16. Do not use overly complicated technical words unless
    they are necessary.
17. Keep the answer focused on the user's question.
18. End with a short useful tip when appropriate.

FORMAT YOUR RESPONSE LIKE THIS:

**Main Topic**

Short direct explanation.

**Important Points**
- Point 1
- Point 2
- Point 3

**What You Should Do**
1. Step one
2. Step two
3. Step three

**Example**
Give a simple example if useful.

Keep the response clean, readable and student-friendly.
"""

            # ------------------------------------------------
            # MODE-SPECIFIC INSTRUCTIONS
            # ------------------------------------------------

            prompts = {

                "general":
                    """
Act as a helpful academic assistant.
Help the student understand subjects,
concepts, assignments and general academic doubts.
""",

                "interview":
                    """
Act as a professional interview coach.

For interview questions:
- Give a strong sample answer.
- Keep it natural enough for a student to speak.
- Explain why the answer is good.
- Give one improvement tip.
- If it is a technical question, explain the concept
  before giving the sample response.
""",

                "placement":
                    """
Act as a placement preparation mentor.

Give:
- Skills to learn
- Topics to prepare
- Practice strategy
- Interview preparation
- A realistic timeline when appropriate

Prioritize the most important things first.
""",

                "project":
                    """
Act as a software project mentor.

Help with:
- Project ideas
- Problem statement
- Technologies
- Architecture
- Features
- Database
- AI/ML integration
- Implementation steps
- Testing
- Deployment

Keep suggestions realistic for a college student.
""",

                "career":
                    """
Act as a career mentor for an AI and Data Science student.

Give:
- Skills roadmap
- Career options
- Technologies to learn
- Project suggestions
- Certification suggestions when useful
- Placement preparation
- Short-term and long-term goals

Be practical rather than giving generic motivation.
""",
            }

            selected_prompt = prompts.get(
                mode,
                prompts["general"],
            )

            # ------------------------------------------------
            # FINAL PROMPT
            # ------------------------------------------------

            final_prompt = (
                base_instruction
                + "\n\n"
                + selected_prompt
                + "\n\n"
                + "USER QUESTION:\n"
                + question
            )

            answer = _openrouter(
                final_prompt,
            )

    return render(
        request,
        "campus/ai.html",
        {
            "answer": answer,
        },
    )
