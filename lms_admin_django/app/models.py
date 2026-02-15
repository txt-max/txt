from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.hashers import make_password, check_password


class UserManager(BaseUserManager):
    def create_user(self, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')

        email = self.normalize_email(email)
        # Удаляем role из extra_fields, если он там есть, чтобы задать его явно,
        # либо позволяем ему просто быть в extra_fields
        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        # Устанавливаем роль в словаре, не передавая её отдельным аргументом
        extra_fields['role'] = 'admin'

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True')

        # Передаем ТОЛЬКО email, full_name и password позиционно.
        # Все остальное (включая role) уйдет в **extra_fields
        return self.create_user(email, full_name, password, **extra_fields)


class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
        ('admin', 'Администратор'),
    ]

    username = None  # Убираем username

    # Поля, соответствующие таблице users в БД
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True, max_length=100)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(blank=True, null=True)

    # Переопределяем стандартное поле password, указывая имя столбца в БД
    password = models.CharField(max_length=255, db_column='password_hash')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'role']

    objects = UserManager()

    class Meta:
        db_table = 'users'  # Имя таблицы в БД
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['full_name']

    def __str__(self):
        return self.full_name


class Group(models.Model):
    """Учебные группы"""

    group_name = models.CharField(max_length=50, unique=True, verbose_name='Название группы')
    curator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'teacher'},
        related_name='curated_groups',
        verbose_name='Куратор'
    )
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'
        ordering = ['group_name']

    def __str__(self):
        return self.group_name


class Course(models.Model):
    """Учебные курсы"""

    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('published', 'Опубликован'),
        ('archived', 'Архивирован'),
    ]

    title = models.CharField(max_length=200, verbose_name='Название курса')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'},
        related_name='courses_created',
        verbose_name='Преподаватель'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Статус')
    start_date = models.DateField(blank=True, null=True, verbose_name='Дата начала')
    end_date = models.DateField(blank=True, null=True, verbose_name='Дата окончания')
    max_students = models.IntegerField(blank=True, null=True, verbose_name='Макс. количество студентов')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_enrolled_count(self):
        """Количество записанных студентов"""
        return self.enrollments.filter(status='active').count()


class Module(models.Model):
    """Модули курса"""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules', verbose_name='Курс')
    title = models.CharField(max_length=200, verbose_name='Название модуля')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    order_num = models.IntegerField(verbose_name='Порядковый номер')
    is_unlocked = models.BooleanField(default=True, verbose_name='Доступен')

    class Meta:
        verbose_name = 'Модуль'
        verbose_name_plural = 'Модули'
        ordering = ['course', 'order_num']
        unique_together = ['course', 'order_num']

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    """Учебные материалы"""

    CONTENT_TYPE_CHOICES = [
        ('text', 'Текст'),
        ('video', 'Видео'),
        ('pdf', 'PDF'),
        ('link', 'Ссылка'),
    ]

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons', verbose_name='Модуль')
    title = models.CharField(max_length=200, verbose_name='Название урока')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, verbose_name='Тип контента')
    content_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='URL контента')
    content_text = models.TextField(blank=True, null=True, verbose_name='Текстовый контент')
    order_num = models.IntegerField(verbose_name='Порядковый номер')
    duration_minutes = models.IntegerField(blank=True, null=True, verbose_name='Продолжительность (мин)')

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['module', 'order_num']

    def __str__(self):
        return self.title


class Quiz(models.Model):
    """Тесты"""

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='quizzes', verbose_name='Модуль')
    title = models.CharField(max_length=200, verbose_name='Название теста')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    max_score = models.IntegerField(verbose_name='Максимальный балл')
    passing_score = models.IntegerField(default=0, verbose_name='Проходной балл')
    time_limit_minutes = models.IntegerField(blank=True, null=True, verbose_name='Лимит времени (мин)')
    is_published = models.BooleanField(default=False, verbose_name='Опубликован')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Тест'
        verbose_name_plural = 'Тесты'
        ordering = ['module', 'created_at']

    def __str__(self):
        return self.title


class Question(models.Model):
    """Вопросы теста"""

    QUESTION_TYPE_CHOICES = [
        ('single', 'Один ответ'),
        ('multiple', 'Несколько ответов'),
        ('text', 'Текстовый ответ'),
    ]

    DIFFICULTY_CHOICES = [
        ('easy', 'Лёгкий'),
        ('medium', 'Средний'),
        ('hard', 'Сложный'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions', verbose_name='Тест')
    question_text = models.TextField(verbose_name='Текст вопроса')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, verbose_name='Тип вопроса')
    points = models.IntegerField(default=1, verbose_name='Баллы')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium', verbose_name='Сложность')
    order_num = models.IntegerField(verbose_name='Порядковый номер')

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['quiz', 'order_num']

    def __str__(self):
        return self.question_text[:50]


class Answer(models.Model):
    """Варианты ответов"""

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers', verbose_name='Вопрос')
    answer_text = models.TextField(verbose_name='Текст ответа')
    is_correct = models.BooleanField(default=False, verbose_name='Правильный ответ')
    order_num = models.IntegerField(verbose_name='Порядковый номер')

    class Meta:
        verbose_name = 'Ответ'
        verbose_name_plural = 'Ответы'
        ordering = ['question', 'order_num']

    def __str__(self):
        return self.answer_text[:50]


class Enrollment(models.Model):
    """Запись студентов на курсы"""

    STATUS_CHOICES = [
        ('active', 'Активен'),
        ('completed', 'Завершён'),
        ('dropped', 'Отозван'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'},
                                related_name='enrollments', verbose_name='Студент')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments', verbose_name='Курс')
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='enrollments',
                              verbose_name='Группа')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='Статус')
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата записи')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения')

    class Meta:
        verbose_name = 'Запись на курс'
        verbose_name_plural = 'Записи на курсы'
        ordering = ['-enrolled_at']
        unique_together = ['student', 'course']

    def __str__(self):
        return f"{self.student.full_name} - {self.course.title}"


class QuizResult(models.Model):
    """Результаты тестов"""

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='results', verbose_name='Тест')
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'},
                                related_name='quiz_results', verbose_name='Студент')
    score = models.IntegerField(verbose_name='Набранный балл')
    max_score = models.IntegerField(verbose_name='Максимальный балл')
    percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Процент выполнения')
    started_at = models.DateTimeField(verbose_name='Время начала')
    submitted_at = models.DateTimeField(verbose_name='Время завершения')
    is_passed = models.BooleanField(default=False, verbose_name='Пройден')

    class Meta:
        verbose_name = 'Результат теста'
        verbose_name_plural = 'Результаты тестов'
        ordering = ['-submitted_at']
        unique_together = ['quiz', 'student']

    def __str__(self):
        return f"{self.student.full_name} - {self.quiz.title}: {self.score}/{self.max_score}"


class StudentProgress(models.Model):
    """Прогресс обучения"""

    STATUS_CHOICES = [
        ('not_started', 'Не начат'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершён'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'},
                                related_name='progress', verbose_name='Студент')
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='progress', verbose_name='Модуль')
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='progress',
                               verbose_name='Урок')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started', verbose_name='Статус')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения')

    class Meta:
        verbose_name = 'Прогресс обучения'
        verbose_name_plural = 'Прогресс обучения'
        ordering = ['-completed_at']
        unique_together = ['student', 'module', 'lesson']

    def __str__(self):
        return f"{self.student.full_name} - {self.module.title}"


class AuditLog(models.Model):
    """Журнал аудита"""

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs',
                             verbose_name='Пользователь')
    action = models.CharField(max_length=50, verbose_name='Действие')
    table_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='Таблица')
    record_id = models.IntegerField(blank=True, null=True, verbose_name='ID записи')
    old_value = models.TextField(blank=True, null=True, verbose_name='Старое значение')
    new_value = models.TextField(blank=True, null=True, verbose_name='Новое значение')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP адрес')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время')

    class Meta:
        verbose_name = 'Запись аудита'
        verbose_name_plural = 'Журнал аудита'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.created_at} - {self.action}"