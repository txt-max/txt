from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Group, Course, Module, Lesson, Quiz, Question, Answer
from .models import Enrollment, QuizResult, StudentProgress, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('full_name', 'phone', 'role')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'created_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'full_name', 'role', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'created_at')
    search_fields = ('email', 'full_name')
    ordering = ('email',)
    readonly_fields = ('created_at',)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('group_name', 'curator', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('group_name', 'curator__full_name')
    autocomplete_fields = ['curator']


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    ordering = ['order_num']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'status', 'start_date', 'end_date', 'get_enrolled_count')
    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('title', 'teacher__full_name', 'description')
    autocomplete_fields = ['teacher']
    inlines = [ModuleInline]

    def get_enrolled_count(self, obj):
        return obj.get_enrolled_count()

    get_enrolled_count.short_description = 'Записано студентов'


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    ordering = ['order_num']


class QuizInline(admin.TabularInline):
    model = Quiz
    extra = 1


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order_num', 'is_unlocked')
    list_filter = ('course', 'is_unlocked')
    search_fields = ('title', 'course__title')
    autocomplete_fields = ['course']
    inlines = [LessonInline, QuizInline]
    ordering = ['course', 'order_num']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'content_type', 'order_num', 'duration_minutes')
    list_filter = ('content_type', 'module__course')
    search_fields = ('title', 'module__title')
    autocomplete_fields = ['module']
    ordering = ['module', 'order_num']


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    ordering = ['order_num']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'max_score', 'passing_score', 'is_published')
    list_filter = ('is_published', 'module__course')
    search_fields = ('title', 'module__title')
    autocomplete_fields = ['module']
    inlines = [QuestionInline]


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1
    ordering = ['order_num']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'quiz', 'question_type', 'points', 'difficulty', 'order_num')
    list_filter = ('question_type', 'difficulty', 'quiz__module__course')
    search_fields = ('question_text', 'quiz__title')
    autocomplete_fields = ['quiz']
    inlines = [AnswerInline]
    ordering = ['quiz', 'order_num']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('answer_text', 'question', 'is_correct', 'order_num')
    list_filter = ('is_correct',)
    search_fields = ('answer_text', 'question__question_text')
    autocomplete_fields = ['question']
    ordering = ['question', 'order_num']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'group', 'status', 'enrolled_at', 'completed_at')
    list_filter = ('status', 'course', 'group', 'enrolled_at')
    search_fields = ('student__full_name', 'student__email', 'course__title')
    autocomplete_fields = ['student', 'course', 'group']
    ordering = ['-enrolled_at']


@admin.register(QuizResult)
class QuizResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'score', 'max_score', 'percentage', 'is_passed', 'submitted_at')
    list_filter = ('is_passed', 'quiz__module__course', 'submitted_at')
    search_fields = ('student__full_name', 'quiz__title')
    autocomplete_fields = ['student', 'quiz']
    ordering = ['-submitted_at']


@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'module', 'lesson', 'status', 'completed_at')
    list_filter = ('status', 'module__course', 'completed_at')
    search_fields = ('student__full_name', 'module__title')
    autocomplete_fields = ['student', 'module', 'lesson']
    ordering = ['-completed_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'table_name', 'record_id', 'ip_address')
    list_filter = ('action', 'table_name', 'created_at')
    search_fields = ('user__full_name', 'user__email', 'action', 'old_value', 'new_value')
    readonly_fields = ('created_at',)
    ordering = ['-created_at']