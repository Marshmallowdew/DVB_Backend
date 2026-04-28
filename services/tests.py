from django.test import TestCase
from django.db.utils import IntegrityError
from branches.models import Branch
from services.models import Service

class ServiceModelTests(TestCase):
    
    def setUp(self):
        self.branch = Branch.objects.create(name="Филиал №1", address="ул. Первая")
        self.branch_2 = Branch.objects.create(name="Филиал №2", address="ул. Вторая")

    def test_create_service_defaults(self):
        """Проверяем, что дефолтные значения (длительность и статус) устанавливаются верно"""
        service = Service.objects.create(
            branch=self.branch,
            name="Диагностика ходовой",
            price=1000.00
        )
        
        # duration_minutes должен быть 60 по умолчанию
        self.assertEqual(service.duration_minutes, 60)
        # is_active должен быть True
        self.assertTrue(service.is_active)
        # Проверяем магический метод __str__
        self.assertEqual(str(service), "Диагностика ходовой - 1000.0 руб. (Филиал №1)")

    def test_service_unique_together_constraint(self):
        """
        Проверяем ограничение unique_together:
        Нельзя создать две услуги с одинаковым именем в ОДНОМ филиале
        """
        # Создаем первую услугу - все Ок
        Service.objects.create(branch=self.branch, name="Замена масла", price=500.00)
        
        # Пытаемся создать такую же услугу в ТОМ ЖЕ филиале
        with self.assertRaises(IntegrityError):
            Service.objects.create(branch=self.branch, name="Замена масла", price=600.00)

    def test_service_same_name_different_branches(self):
        """
        Проверяем, что можно создать услуги с одинаковым именем, 
        если они находятся в РАЗНЫХ филиалах
        """
        Service.objects.create(branch=self.branch, name="Замена масла", price=500.00)
        # Создаем в branch_2 - должно пройти успешно, ошибки не будет
        service_2 = Service.objects.create(branch=self.branch_2, name="Замена масла", price=600.00)
        
        self.assertEqual(Service.objects.count(), 2)
        self.assertEqual(service_2.price, 600.00)