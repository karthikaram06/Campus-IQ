from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from campus import views


urlpatterns = [

    # ========================================================
    # ADMIN
    # ========================================================

    path(
        "admin/",
        admin.site.urls,
    ),


    # ========================================================
    # HOME
    # ========================================================

    path(
        "",
        views.home,
        name="home",
    ),


    # ========================================================
    # STUDENT
    # ========================================================

    path(
        "student/register/",
        views.student_register,
        name="student_register",
    ),

    path(
        "student/login/",
        views.student_login,
        name="student_login",
    ),

    path(
        "student/logout/",
        views.logout_view,
        name="student_logout",
    ),

    path(
        "student/dashboard/",
        views.student_dashboard,
        name="student_dashboard",
    ),

    path(
        "student/attendance/",
        views.student_attendance,
        name="student_attendance",
    ),

    path(
        "student/timetable/",
        views.student_timetable,
        name="student_timetable",
    ),

    path(
        "student/leave/",
        views.student_leave,
        name="student_leave",
    ),


    # ========================================================
    # TEACHER
    # ========================================================

    path(
        "teacher/register/",
        views.teacher_register,
        name="teacher_register",
    ),

    path(
        "teacher/login/",
        views.teacher_login,
        name="teacher_login",
    ),

    path(
        "teacher/logout/",
        views.logout_view,
        name="teacher_logout",
    ),

    path(
        "teacher/dashboard/",
        views.teacher_dashboard,
        name="teacher_dashboard",
    ),

    path(
        "teacher/student/<int:student_id>/",
        views.teacher_student_detail,
        name="teacher_student_detail",
    ),

    path(
        "teacher/student/<int:student_id>/verify/<str:action>/",
        views.teacher_verify_student,
        name="teacher_verify_student",
    ),

    path(
        "teacher/attendance/<int:classroom_id>/<int:subject_id>/",
        views.teacher_attendance,
        name="teacher_attendance",
    ),

    path(
        "teacher/marks/<int:classroom_id>/<int:subject_id>/",
        views.teacher_marks,
        name="teacher_marks",
    ),

    path(
        "teacher/achievement/<int:student_id>/",
        views.teacher_add_achievement,
        name="teacher_add_achievement",
    ),

    path(
        "teacher/leave/<int:leave_id>/<str:action>/",
        views.teacher_leave_action,
        name="teacher_leave_action",
    ),

    # ========================================================
    # TEACHER TIMETABLE
    # ========================================================

    path(
        "teacher/timetable/<int:classroom_id>/",
        views.teacher_timetable,
        name="teacher_timetable",
    ),


    # ========================================================
    # AI
    # ========================================================

    path(
        "ai/",
        views.ai_assistant,
        name="ai_assistant",
    ),

] + static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT,
)