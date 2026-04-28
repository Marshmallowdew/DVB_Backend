from django.db import models
from branches.models import Branch, Department

class Service(models.Model):
    # Модель услуги
    branch = models.ForeignKey(
        Branch, 
        on_delete=models.CASCADE, 
        related_name='services',
        verbose_name='Филиал'
    )
    name = models.CharField(max_length=150, verbose_name='Название услуги')
    description = models.TextField(blank=True, verbose_name='Описание услуги')
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Стоимость (руб.)'
    )
    duration_minutes = models.PositiveIntegerField(
        default=60, 
        verbose_name='Примерная длительность (в минутах)'
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Услуга активна'
    )

    department = models.ForeignKey('branches.Department', on_delete=models.CASCADE, related_name='services', null=True, blank=True, verbose_name="Отдел")
    
    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        unique_together = ('branch', 'name') 
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.price} руб. ({self.branch.name})"


class Mechanic(models.Model):
    # Модель мастера
    branch = models.ForeignKey(
        Branch, 
        on_delete=models.CASCADE, 
        related_name='mechanics',
        verbose_name='Филиал'
    )
    first_name = models.CharField(max_length=50, verbose_name='Имя')
    last_name = models.CharField(max_length=50, verbose_name='Фамилия')
    departments = models.ManyToManyField(Department, related_name='mechanics', blank=True)
    experience_years = models.PositiveIntegerField(
        default=0, 
        verbose_name='Опыт (лет)'
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Работает в данный момент',
        help_text='Уберите галочку, если мастер уволен или в долгом отпуске'
    )

    class Meta:
        verbose_name = 'Мастер'
        verbose_name_plural = 'Мастера'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.branch.name}"
