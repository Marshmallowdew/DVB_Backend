from django.db import models
from django.conf import settings
from django.utils import timezone
from branches.models import Branch, Box
from services.models import Service, Mechanic
from datetime import timedelta
import string
import random

class Order(models.Model):
    # Модель заказ-наряда
    class Statuses(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        CONFIRMED = 'confirmed', 'Подтверждена'
        IN_PROGRESS = 'in_progress', 'В работе'
        COMPLETED = 'completed', 'Выполнено'
        CANCELLED = 'cancelled', 'Отменено'
    
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name='Итоговая стоимость'
    )

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Клиент',
        null=True, 
        blank=True
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Филиал'
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL, 
        null=True,
        related_name='orders',
        verbose_name='Услуга'
    )
    mechanic = models.ForeignKey(
        Mechanic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Мастер'
    )
    phone_number = models.CharField(max_length=20, blank=True, verbose_name='Телефон клиента (если нет аккаунта)')
    
    # === ПОЛЯ ДЛЯ ОФФЛАЙН ПРИВЯЗКИ ===
    linking_pin = models.CharField(max_length=6, null=True, blank=True, verbose_name='PIN для привязки')
    pin_expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Срок действия PIN')
    is_linked = models.BooleanField(default=False, verbose_name='Привязан к аккаунту')

    car_brand = models.CharField(max_length=100, verbose_name='Марка авто', default='Не указана')
    car_model = models.CharField(max_length=100, verbose_name='Модель авто', default='Не указана')
    car_number = models.CharField(max_length=10, blank=True, verbose_name='Гос. номер')
    car_vin = models.CharField(max_length=17, blank=True, verbose_name='VIN-код')
    
    appointment_time = models.DateTimeField()
    duration_minutes = models.IntegerField() 

    mechanic = models.ForeignKey(Mechanic, on_delete=models.SET_NULL, null=True, blank=True)
    box = models.ForeignKey(Box, on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Statuses.choices,
        default=Statuses.PENDING,
        verbose_name='Статус заказа'
    )
    client_comment = models.TextField(
        blank=True, 
        verbose_name='Комментарий клиента'
    )
    admin_comment = models.TextField(
        blank=True, 
        verbose_name='Комментарий администратора'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания записи')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    def generate_linking_pin(self):
        """Генерирует случайный 6-значный цифро-буквенный PIN-код и ставит срок жизни 3 месяца"""
        if not self.linking_pin:
            chars = string.ascii_uppercase + string.digits
            self.linking_pin = ''.join(random.choice(chars) for _ in range(6))
            # 3 месяца (~90 дней)
            self.pin_expires_at = timezone.now() + timedelta(days=90)
            self.save(update_fields=['linking_pin', 'pin_expires_at'])

    class Meta:
        verbose_name = 'Заказ-наряд'
        verbose_name_plural = 'Заказ-наряды'
        ordering = ['-appointment_time']

    def __str__(self):
        service_name = self.service.name if self.service else "Услуга удалена"
        return f"Заказ #{self.id} | {self.client.phone_number} | {service_name} | {self.get_status_display()}"
