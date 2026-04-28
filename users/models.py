from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from django.db import models
from orders.models import Order

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        
        email = self.normalize_email(email)
        
        phone_number = extra_fields.get('phone_number')
        if phone_number:
            from .services import normalize_phone_number
            try:
                extra_fields['phone_number'] = normalize_phone_number(phone_number)
            except ValueError as e:
                raise ValueError(f"Ошибка в номере телефона: {e}")

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'main_admin') 

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')
            
        # номер телефона для суперпользователя
        if not extra_fields.get('phone_number'):
            raise ValueError('Для суперпользователя номер телефона обязателен.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Roles(models.TextChoices):
        USER = 'user', 'Пользователь'
        MANAGER = 'manager', 'Менеджер отдела'
        SERVICE_ADMIN = 'service_admin', 'Администратор сервиса'
        MAIN_ADMIN = 'main_admin', 'Главный администратор'

    username = None

    phone_number = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name='Номер телефона',
        blank=True,
        null=True,
    )

    email = models.EmailField(
        verbose_name='email address',
        unique=True,
        blank=False,
        null=False
    )

    middle_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='Отчество')

    role = models.CharField(
        max_length=20, 
        choices=Roles.choices, 
        default=Roles.USER,
        verbose_name='Роль пользователя'
    )
    
    is_phone_verified = models.BooleanField(
        default=True, 
        verbose_name='Телефон подтвержден'
    )

    branch = models.ForeignKey(
        'branches.Branch',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="admins",
        verbose_name="Филиал"
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number'] 

    objects = CustomUserManager()

    departments = models.ManyToManyField('branches.Department', blank=True, related_name='managers', verbose_name="Отделы менеджера")
    
    def __str__(self):
        return f"{self.email} - {self.get_role_display()}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class Car(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='cars',
        verbose_name='Владелец'
    )
    brand = models.CharField(max_length=100, verbose_name='Марка')
    model = models.CharField(max_length=100, verbose_name='Модель')
    number = models.CharField(max_length=20, blank=True, null=True, verbose_name='Гос. номер')
    vin_number = models.CharField(max_length=17, blank=True, null=True, verbose_name='VIN-код')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        verbose_name = 'Автомобиль'
        verbose_name_plural = 'Автомобили клиентов'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.brand} {self.model} ({self.number or 'Без номера'})"