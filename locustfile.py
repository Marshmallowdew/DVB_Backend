import random
from datetime import datetime, timedelta
from locust import HttpUser, task, between

class AutoServiceUser(HttpUser):
    # Пауза между действиями пользователя (от 1 до 3 секунд)
    wait_time = between(1, 3)
    
    # Нужно скопировать access token
    token = ""

    def on_start(self):
        """Выполняется один раз при старте"""
        self.client.get("/api/branches/")
        self.client.get("/api/services/")

    @task(3)
    def view_services(self):
        """Чаще всего пользователи просто смотрят услуги"""
        self.client.get("/api/services/")

    @task(2)
    def check_slots(self):
        """Поиск свободных слотов"""
        self.client.get("/api/orders/available-slots/?branch_id=1&service_id=1&date=2026-04-10")   # изменить дату

    @task(1)
    def admin_view_orders(self):
        """Админ просматривает список заказов"""
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/api/orders/?branch=1", headers=headers)

    @task(1)
    def create_order(self):
        random_days = random.randint(1, 14)
        future_date = (datetime.now() + timedelta(days=random_days)).strftime('%Y-%m-%d')
        
        branch_id = 15
        service_id = 13

        slots_response = self.client.get(
            f"/api/orders/available-slots/?branch_id={branch_id}&service_id={service_id}&date={future_date}",
            name="/api/orders/available-slots/ (before POST)"
        )
        
        if slots_response.status_code == 200:
            data = slots_response.json()
            slots = data.get("slots", [])
            
            if slots:
                random_slot = random.choice(slots)
                appointment_time = f"{future_date}T{random_slot}:00Z"
                
                payload = {
                    "branch": branch_id,
                    "service": service_id,
                    "appointment_time": appointment_time,
                    "car_brand": "Toyota",
                    "car_model": "Camry",
                    "client_first_name": "Тест",
                    "client_last_name": "Локустов",
                    "client_phone": f"8999{random.randint(1000000, 9999999)}"
                }

                headers = {"Authorization": f"Bearer {self.token}"}
                
                with self.client.post("/api/orders/", json=payload, headers=headers, catch_response=True) as response:
                    if response.status_code not in [200, 201]:
                        response.failure(f"Ошибка создания: {response.status_code} - {response.text}")
                    else:
                        response.success()
            else:
                print(f"Слотов на {future_date} нет. Пропускаем POST.")
        else:
            print(f"Ошибка при поиске слотов: {slots_response.status_code} - {slots_response.text}")