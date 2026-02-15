from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Avg, Q
from .models import User, Group, Course, Enrollment, QuizResult, AuditLog
from .forms import CustomUserCreationForm, CustomUserChangeForm, CourseForm, GroupForm


# Декоратор для проверки роли администратора
def admin_required(function):
    return user_passes_test(lambda u: u.is_authenticated and u.role == 'admin')(function)


# Декоратор для проверки роли преподавателя или администратора
def teacher_or_admin_required(function):
    return user_passes_test(lambda u: u.is_authenticated and u.role in ['teacher', 'admin'])(function)


@login_required
def dashboard_view(request):
    """Панель управления"""

    # Статистика
    total_users = User.objects.count()
    total_students = User.objects.filter(role='student').count()
    total_teachers = User.objects.filter(role='teacher').count()
    total_courses = Course.objects.count()
    active_courses = Course.objects.filter(status='published').count()
    total_enrollments = Enrollment.objects.filter(status='active').count()

    # Последние записи
    recent_enrollments = Enrollment.objects.select_related('student', 'course') \
        .filter(status='active').order_by('-enrolled_at')[:10]

    # Курсы с наибольшим количеством студентов
    popular_courses = Course.objects.annotate(
        student_count=Count('enrollments', filter=Q(enrollments__status='active'))
    ).order_by('-student_count')[:5]

    # Статистика по результатам тестов
    avg_score = QuizResult.objects.aggregate(Avg('percentage'))['percentage__avg'] or 0

    context = {
        'total_users': total_users,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_courses': total_courses,
        'active_courses': active_courses,
        'total_enrollments': total_enrollments,
        'avg_score': round(avg_score, 2),
        'recent_enrollments': recent_enrollments,
        'popular_courses': popular_courses,
    }

    return render(request, 'dashboard/index.html', context)


@admin_required
def users_list_view(request):
    """Список пользователей"""

    # Фильтрация
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')

    users = User.objects.all()

    if role:
        users = users.filter(role=role)
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    if search:
        users = users.filter(
            Q(full_name__icontains=search) |
            Q(email__icontains=search)
        )

    users = users.order_by('full_name')

    context = {
        'users': users,
        'selected_role': role,
        'selected_status': status,
        'search_query': search,
    }

    return render(request, 'users/list.html', context)


@admin_required
def users_create_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Пользователь {user.full_name} успешно создан')
            return redirect('app:users_list')
    else:
        form = CustomUserCreationForm()

    context = {'form': form}
    return render(request, 'users/create.html', context)


@admin_required
def users_edit_view(request, user_id):
    """Редактирование пользователя"""

    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()

            # Обработка смены пароля
            password = request.POST.get('password')
            if password:
                password_confirm = request.POST.get('password_confirm')
                if password != password_confirm:
                    messages.error(request, 'Пароли не совпадают')
                    return redirect('app:users_edit', user_id=user_id)

                if len(password) < 6:
                    messages.error(request, 'Пароль должен содержать не менее 6 символов')
                    return redirect('app:users_edit', user_id=user_id)

                user.set_password(password)
                user.save()

            messages.success(request, f'Пользователь {user.full_name} успешно обновлён')
            return redirect('app:users_list')
    else:
        form = CustomUserChangeForm(instance=user)

    context = {'form': form, 'user': user}
    return render(request, 'users/edit.html', context)


@admin_required
def users_delete_view(request, user_id):
    """Удаление пользователя"""

    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        full_name = user.full_name
        user.delete()
        messages.success(request, f'Пользователь {full_name} успешно удалён')
        return redirect('app:users_list')

    context = {'user': user}
    return render(request, 'users/delete_confirm.html', context)


@teacher_or_admin_required
def courses_list_view(request):
    """Список курсов"""

    # Фильтрация
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')

    courses = Course.objects.select_related('teacher')

    if status:
        courses = courses.filter(status=status)
    if search:
        courses = courses.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(teacher__full_name__icontains=search)
        )

    courses = courses.order_by('-created_at')

    # Статистика для каждого курса
    for course in courses:
        course.enrolled_count = course.enrollments.filter(status='active').count()
        course.completed_count = course.enrollments.filter(status='completed').count()

    context = {
        'courses': courses,
        'selected_status': status,
        'search_query': search,
    }

    return render(request, 'courses/list.html', context)


@teacher_or_admin_required
def courses_create_view(request):
    """Создание курса"""

    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, f'Курс "{course.title}" успешно создан')
            return redirect('app:courses_list')
    else:
        form = CourseForm()

    context = {'form': form}
    return render(request, 'courses/create.html', context)


@teacher_or_admin_required
def courses_detail_view(request, course_id):
    """Детали курса"""

    course = get_object_or_404(Course.objects.select_related('teacher'), pk=course_id)
    modules = course.modules.all().prefetch_related('lessons', 'quizzes')

    # Статистика
    enrolled_count = course.enrollments.filter(status='active').count()
    completed_count = course.enrollments.filter(status='completed').count()
    avg_score = QuizResult.objects.filter(
        quiz__module__course=course
    ).aggregate(Avg('percentage'))['percentage__avg'] or 0

    context = {
        'course': course,
        'modules': modules,
        'enrolled_count': enrolled_count,
        'completed_count': completed_count,
        'avg_score': round(avg_score, 2),
    }

    return render(request, 'courses/detail.html', context)


@admin_required
def groups_list_view(request):
    """Список групп"""

    groups = Group.objects.select_related('curator').annotate(
        student_count=Count('enrollments')
    ).order_by('group_name')

    context = {'groups': groups}
    return render(request, 'groups/list.html', context)


@login_required
def reports_view(request):
    """Отчёты"""

    # Статистика по курсам
    course_stats = Course.objects.annotate(
        total_enrolled=Count('enrollments', filter=Q(enrollments__status='active')),
        completed=Count('enrollments', filter=Q(enrollments__status='completed')),
        avg_score=Avg('modules__quizzes__results__percentage')
    ).order_by('-created_at')[:20]

    # Статистика по пользователям
    user_stats = User.objects.filter(role='student').annotate(
        courses_count=Count('enrollments', filter=Q(enrollments__status='active')),
        completed_courses=Count('enrollments', filter=Q(enrollments__status='completed')),
        avg_score=Avg('quiz_results__percentage')
    ).order_by('-courses_count')[:20]

    context = {
        'course_stats': course_stats,
        'user_stats': user_stats,
    }

    return render(request, 'reports/index.html', context)


@admin_required
def audit_log_view(request):
    """Журнал аудита"""

    # Фильтрация
    action = request.GET.get('action', '')
    user_id = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    logs = AuditLog.objects.select_related('user').all()

    if action:
        logs = logs.filter(action=action)
    if user_id:
        logs = logs.filter(user_id=user_id)
    if date_from:
        logs = logs.filter(created_at__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__lte=date_to + ' 23:59:59')

    logs = logs.order_by('-created_at')[:100]

    users = User.objects.all().order_by('full_name')

    context = {
        'logs': logs,
        'users': users,
        'selected_action': action,
        'selected_user': user_id,
        'date_from': date_from,
        'date_to': date_to,
    }

    return render(request, 'audit/list.html', context)