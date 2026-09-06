from django.contrib.auth.models import User
from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)
    def __str__(self): return f'{self.code} - {self.name}'

class TeacherProfile(models.Model):
    STATUS_CHOICES = [('PENDING','Pending'),('APPROVED','Approved'),('REJECTED','Rejected')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    employee_id = models.CharField(max_length=40, unique=True)
    email = models.EmailField()
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='teachers')
    designation = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    def __str__(self): return f'{self.employee_id} - {self.user.get_full_name() or self.user.username}'

class Classroom(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='classrooms')
    year = models.CharField(max_length=20)
    section = models.CharField(max_length=10)
    academic_year = models.CharField(max_length=20, default='2026-2027')
    room_number = models.CharField(max_length=40, blank=True)
    capacity = models.PositiveIntegerField(default=65)
    teacher_one = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='classrooms_one')
    teacher_two = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='classrooms_two')
    active = models.BooleanField(default=True)
    def __str__(self): return self.name

class StudentProfile(models.Model):
    STATUS_CHOICES = [('PENDING','Pending'),('APPROVED','Approved'),('REJECTED','Rejected'),('BLOCKED','Blocked')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    register_number = models.CharField(max_length=30, unique=True)
    email = models.EmailField()
    college = models.CharField(max_length=180, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    year = models.CharField(max_length=20, blank=True)
    section = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    def __str__(self): return f'{self.register_number} - {self.user.get_full_name() or self.user.username}'

class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=160)
    credits = models.PositiveIntegerField(default=3)
    semester = models.PositiveIntegerField(default=5)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='subjects')
    def __str__(self): return f'{self.code} - {self.name}'

class Mark(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='marks')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='marks')
    internal = models.PositiveIntegerField(default=0)
    external = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['student','subject'], name='unique_student_subject_mark')]
    @property
    def total(self): return self.internal + self.external

class Attendance(models.Model):
    STATUS_CHOICES = [('P','Present'),('A','Absent'),('L','Leave')]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attendance_records')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['student','subject','date'], name='unique_daily_attendance')]
        ordering = ['-date']
    @classmethod
    def percentage(cls, student, subject=None):
        qs = cls.objects.filter(student=student)
        if subject: qs = qs.filter(subject=subject)
        total = qs.exclude(status='L').count()
        present = qs.filter(status='P').count()
        return round((present / total) * 100, 1) if total else 0

class LeaveRequest(models.Model):
    STATUS_CHOICES = [('PENDING','Pending'),('APPROVED','Approved'),('REJECTED','Rejected')]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='leave_requests')
    from_date = models.DateField()
    to_date = models.DateField()
    reason = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    reviewed_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class TimetableEntry(models.Model):
    DAYS = [('MON','Monday'),('TUE','Tuesday'),('WED','Wednesday'),('THU','Thursday'),('FRI','Friday'),('SAT','Saturday')]
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='timetable')
    day = models.CharField(max_length=3, choices=DAYS)
    period = models.PositiveIntegerField(default=1)
    time = models.CharField(max_length=40, default='09:00 - 10:00')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='timetable_entries')
    custom_subject = models.CharField(max_length=160, blank=True)
    room = models.CharField(max_length=40, blank=True)
    faculty = models.CharField(max_length=120, blank=True)
    class Meta:
        ordering = ['day','period']
        constraints = [models.UniqueConstraint(fields=['classroom','day','period'], name='unique_classroom_day_period')]
    @property
    def display_subject(self): return self.custom_subject or (self.subject.name if self.subject else 'Free Period')

class Achievement(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=180)
    issuer = models.CharField(max_length=160, blank=True)
    date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

class Project(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    tech_stack = models.CharField(max_length=250, blank=True)
    link = models.URLField(blank=True)
    status = models.CharField(max_length=40, default='In Progress')
    created_at = models.DateTimeField(auto_now_add=True)

class AuditLog(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=120)
    object_type = models.CharField(max_length=120)
    object_id = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
