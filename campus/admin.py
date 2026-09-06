from django.contrib import admin
from .models import (
    Department, TeacherProfile, Classroom, StudentProfile, Subject, Mark,
    Attendance, LeaveRequest, TimetableEntry, Achievement, Project, AuditLog,
)

admin.site.site_header = "CampusIQ Administration"
admin.site.site_title = "CampusIQ Admin"
admin.site.index_title = "College Management Control Center"


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "user", "department", "designation", "status", "login_status")
    list_filter = ("status", "department")
    search_fields = ("employee_id", "user__username", "user__first_name", "user__last_name", "email")
    list_editable = ("status",)

    @admin.display(boolean=True, description="Login Active")
    def login_status(self, obj):
        return obj.user.is_active

    def save_model(self, request, obj, form, change):
        # One source of truth: approval controls teacher login automatically.
        super().save_model(request, obj, form, change)
        obj.user.is_active = obj.status == "APPROVED"
        obj.user.save(update_fields=["is_active"])


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "year", "section", "teacher_one", "teacher_two", "capacity", "active")
    list_filter = ("department", "year", "active")
    search_fields = ("name", "section", "academic_year")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("register_number", "user", "department", "classroom", "status", "cgpa", "login_status")
    list_filter = ("status", "department", "classroom")
    search_fields = ("register_number", "user__username", "user__first_name", "email")
    list_editable = ("status",)

    @admin.display(boolean=True, description="Login Active")
    def login_status(self, obj):
        return obj.user.is_active

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.user.is_active = obj.status == "APPROVED"
        obj.user.save(update_fields=["is_active"])


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "semester", "credits")
    list_filter = ("department", "semester")
    search_fields = ("code", "name")


@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "internal", "external", "total", "updated_at")
    list_filter = ("subject", "subject__department")
    search_fields = ("student__register_number", "student__user__first_name", "subject__code")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "date", "status", "teacher")
    list_filter = ("date", "status", "subject")
    search_fields = ("student__register_number", "student__user__first_name")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("student", "from_date", "to_date", "reason", "status", "reviewed_by", "created_at")
    list_filter = ("status",)
    search_fields = ("student__register_number", "reason")


@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ("classroom", "day", "period", "time", "subject", "custom_subject", "room", "faculty")
    list_filter = ("classroom", "day")
    search_fields = ("classroom__name", "room", "faculty", "custom_subject")


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("student", "title", "issuer", "date")
    search_fields = ("student__register_number", "student__user__first_name", "title")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("student", "title", "status", "created_at")
    search_fields = ("student__register_number", "student__user__first_name", "title")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "object_type", "object_id", "created_at")
    readonly_fields = ("created_at",)
