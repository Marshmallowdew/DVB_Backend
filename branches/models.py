from django.db import models
from django.conf import settings
import datetime

class Branch(models.Model):
    name = models.CharField(max_length=150, verbose_name='Название филиала')
    address = models.CharField(max_length=255, verbose_name='Физический адрес')
    
    phone_number = models.CharField(max_length=20, verbose_name='Контактный телефон 1')
    
    phone_number_2 = models.CharField(max_length=20, blank=True, null=True, verbose_name='Контактный телефон 2')
    
    opening_time = models.TimeField(default=datetime.time(9, 0), verbose_name='Время открытия')
    closing_time = models.TimeField(default=datetime.time(20, 0), verbose_name='Время закрытия')
    
    is_active = models.BooleanField(default=True, verbose_name='Филиал работает')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        verbose_name = 'Филиал'
        verbose_name_plural = 'Филиалы'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.opening_time.strftime('%H:%M')} - {self.closing_time.strftime('%H:%M')})"


class ServiceAdminProfile(models.Model):
    # Профиль администратора конкретного сервиса.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='admin_profile',
        verbose_name='Пользователь (Админ)'
    )
    
    branch = models.ForeignKey(
        Branch, 
        on_delete=models.CASCADE, 
        related_name='administrators',
        verbose_name='Управляемый филиал'
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата назначения')

    class Meta:
        verbose_name = 'Профиль администратора филиала'
        verbose_name_plural = 'Профили администраторов филиалов'

    def __str__(self):
        return f"{self.user.phone_number} -> {self.branch.name}"

class Department(models.Model):
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=150, verbose_name="Название категории")
    def __str__(self):
        return f"{self.name} ({self.branch.name})"

class Box(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название бокса/поста")
    branch = models.ForeignKey(
        'Branch', 
        on_delete=models.CASCADE, 
        related_name='boxes',
        verbose_name="Филиал"
    )
    # Бокс может относиться к нескольким отделам
    departments = models.ManyToManyField(
        'Department', 
        related_name='boxes', 
        blank=True,
        verbose_name="Отделы (для которых подходит бокс)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Бокс / Пост"
        verbose_name_plural = "Боксы / Посты"

    def __str__(self):
        return f"{self.name} ({self.branch.name})"