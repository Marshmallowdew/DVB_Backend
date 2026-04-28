from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserManagerTests(TestCase):
    
    def test_create_user_success(self):
        """Проверяем успешное создание обычного пользователя"""
        user = User.objects.create_user(
            phone_number="89991112233",
            email="TESTING@DOMAIN.COM", 
            password="secure_password"
        )
        
        # Проверяем, что пользователь сохранился
        self.assertEqual(User.objects.count(), 1)
        # Проверяем нормализацию email (домен должен стать маленьким)
        self.assertEqual(user.email, "TESTING@domain.com")
        # Проверяем хэширование пароля
        self.assertTrue(user.check_password("secure_password"))
        self.assertFalse(user.check_password("wrong_password"))
        # Проверяем дефолтную роль
        self.assertEqual(user.role, 'user')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_without_phone(self):
        """Проверяем, что нельзя создать пользователя без номера телефона"""
        with self.assertRaisesMessage(ValueError, 'Номер телефона обязателен'):
            User.objects.create_user(
                phone_number="",
                email="test@test.com",
                password="123"
            )

    def test_create_superuser_success(self):
        """Проверяем успешное создание суперпользователя"""
        admin = User.objects.create_superuser(
            phone_number="89990000000",
            email="admin@test.com",
            password="superpassword"
        )
        
        # Проверяем права и роль
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, 'main_admin')

    def test_create_superuser_invalid_flags(self):
        """Проверяем защиту от случайного снятия прав суперадмина при создании"""
        with self.assertRaisesMessage(ValueError, 'Суперпользователь должен иметь is_staff=True.'):
            User.objects.create_superuser(
                phone_number="89990000000",
                email="admin@test.com",
                password="123",
                is_staff=False
            )