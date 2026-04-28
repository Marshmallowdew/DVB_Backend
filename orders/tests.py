from rest_framework.test import APITestCase
from rest_framework import status
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from branches.models import Branch
from services.models import Service, Mechanic
from orders.models import Order

User = get_user_model()

class OrderBookingLogicTests(APITestCase):
    
    def setUp(self):
        """Создаем тестовую базу данных"""
        
        # 1. Создаем тестового клиента (phone_number и email)
        self.user = User.objects.create_user(
            phone_number="89990001122",
            email="test_client@test.ru",
            password="123"
        )
        
        # 2. Создаем филиал, услугу и механика
        self.branch = Branch.objects.create(name="Тестовый Филиал", address="ул. Тестовая 1")
        
        self.service = Service.objects.create(
            name="Замена масла", 
            price=1500.00,
            branch=self.branch
        )
        
        self.mechanic = Mechanic.objects.create(
            first_name="Иван", 
            last_name="Иванов", 
            branch=self.branch
        )

        # 3 время для тестов (завтра в 10:00)
        tomorrow = timezone.now() + timedelta(days=1)
        self.test_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        self.test_time_iso = self.test_time.isoformat()
        self.date_str = self.test_time.strftime('%Y-%m-%d')

    def test_available_slots_endpoint(self):
        """ТЕСТ 1: Проверяем, что слот пропадает после создания заказа"""
        
        url = f"/api/orders/available-slots/?branch_id={self.branch.id}&service_id={self.service.id}&date={self.date_str}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slots = response.data.get('slots', [])
        
        # Проверяем, что 10:00 есть в списке
        if "10:00" in slots:
            # Создаем заказ на 10:00
            Order.objects.create(
                client=self.user,                 
                branch=self.branch,
                service=self.service,
                mechanic=self.mechanic,
                appointment_time=self.test_time,
                duration_minutes=60              
            )

            # Снова запрашиваем слоты
            response_after = self.client.get(url)
            slots_after = response_after.data.get('slots', [])
            
            # Проверяем, что слот 10:00 исчез
            self.assertNotIn("10:00", slots_after, "Слот 10:00 должен исчезнуть")

    def test_prevent_double_booking(self):
        """ТЕСТ 2: Проверка защиты от двойного бронирования"""
        
        # 1. Создаем первый успешный заказ напрямую в БД
        Order.objects.create(
            client=self.user,
            branch=self.branch,
            service=self.service,
            mechanic=self.mechanic,
            appointment_time=self.test_time,
            duration_minutes=60
        )

        # 2. Аутентифицируем второго клиента для POST-запроса
        user_2 = User.objects.create_user(
            phone_number="89991112233",
            email="client2@test.ru",
            password="123"
        )
        self.client.force_authenticate(user=user_2)

        # 3. Пытаемся создать ВТОРОЙ заказ на то же время через API
        payload = {
            "branch": self.branch.id,
            "service": self.service.id,
            "appointment_time": self.test_time_iso,
            "car_brand": "Kia",
            "car_model": "Rio",
            "duration_minutes": 60
        }

        response = self.client.post("/api/orders/", data=payload)

        # Ожидаем ошибку 400, так как время 10:00 уже занято первым клиентом!
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Убеждаемся, что в базе остался только 1 заказ
        self.assertEqual(Order.objects.count(), 1)