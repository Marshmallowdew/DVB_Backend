import re
import random
from users.models import User
from django.utils.crypto import get_random_string
from django.core.cache import cache

def normalize_phone_number(phone):
    # Очищаем от всего, кроме цифр и плюса
    phone = re.sub(r'[^\d+]', '', str(phone))
    
    # Если номер начинается с 8 и длина 11 цифр (например 89991234567)
    if phone.startswith('8') and len(phone) == 11:
        return '+7' + phone[1:]
        
    # Если номер начинается с 7 (например 79991234567)
    elif phone.startswith('7') and len(phone) == 11:
        return '+' + phone
        
    # Если номер уже начинается с +7 (например +79991234567)
    elif phone.startswith('+7') and len(phone) == 12:
        return phone
        
    if len(phone) < 10:
         raise ValueError("Некорректный номер телефона.")
         
    # Для всех остальных форматов, которые уже содержат +
    if not phone.startswith('+'):
        return '+' + phone
        
    return phone

def generate_random_password(length=10):
    return get_random_string(length)

def generate_and_save_otp(email: str) -> str:
    # Генерируем 6 цифр
    otp_code = str(random.randint(100000, 999999))
    
    # Ключ в Redis
    cache_key = f"otp_{email.lower()}"
    
    # Сохраняем на 900 секунд (15 минут)
    cache.set(cache_key, otp_code, timeout=900)
    return otp_code

def verify_and_delete_otp(email: str, entered_otp: str) -> bool:
    cache_key = f"otp_{email.lower()}"
    saved_otp = cache.get(cache_key)
    
    # Если код есть в Redis и совпадает с введенным
    if saved_otp is not None and str(saved_otp) == str(entered_otp):
        cache.delete(cache_key) # Сжигаем код
        return True
        
    return False

def register_new_client(phone_number: str, email: str = None) -> tuple[User, str]:
    # Регистрирует нового клиента и генерирует пароль для авторизации.
    # Возвращает кортеж: (объект пользователя, сгенерированный пароль)

    password = generate_random_password()

    if email is None:
        email = ""
    
    user = User.objects.create_user(
        phone_number=phone_number,
        password=password,
        email=email,
        role=User.Roles.USER
    )
    
    print(f"\n[DEV] СГЕНЕРИРОВАН ПАРОЛЬ ДЛЯ {phone_number}: {password}\n")

    return user, password
