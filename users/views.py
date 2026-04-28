from django.core.cache import cache
from rest_framework import status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.generics import RetrieveUpdateAPIView
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import send_mail

from .serializers import RegisterUserSerializer, UserSerializer, ManagerSerializer, AdminSerializer, OTPRequestSerializer, OTPVerifySerializer, NotificationSerializer, CarSerializer
from .services import register_new_client, generate_and_save_otp, verify_and_delete_otp
from .models import Notification, Car

User = get_user_model()

class RequestOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        # Создаем уникальный ключ для этого email в кеше
        cache_key = f"otp_cooldown_{email}"
        
        # Если такой ключ уже есть в кеше, значит минута еще не прошла
        if cache.get(cache_key):
            return Response(
                {"detail": "Код уже отправлен. Пожалуйста, подождите 1 минуту перед повторным запросом."}, 
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Генерируем и сохраняем код в Redis
        otp_code = generate_and_save_otp(email)
        
        # Отправляем письмо
        send_mail(
            subject='Код для входа на сайт',
            message=f'Ваш одноразовый код: {otp_code}. Он действует 15 минут.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
        # Записываем ключ в кеш. Через 60 секунд он автоматически исчезнет.
        cache.set(cache_key, True, timeout=60)
        
        return Response({"detail": "Код отправлен на почту"}, status=status.HTTP_200_OK)

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        
        if not verify_and_delete_otp(email, otp):
            return Response(
                {"detail": "Неверный код или срок его действия истек"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        user, created = User.objects.get_or_create(email=email)
        if created:
            user.set_unusable_password() 
            user.save()
            
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'is_new_user': created 
        }, status=status.HTTP_200_OK)

# для обновления токена
class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # Достаем refresh токен из куки, а не из тела запроса
        refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            raise InvalidToken("Отсутствует refresh токен в cookies")
            
        request.data['refresh'] = refresh_token
        
        # Вызываем стандартную логику проверки
        response = super().post(request, *args, **kwargs)
        
        # Если в ответе пришел новый refresh токен 
        if response.status_code == 200 and 'refresh' in response.data:
            # Обновляем куку
            response.set_cookie(
                key='refresh_token',
                value=refresh_token, # или response.data['refresh']
                max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
                httponly=True,
                samesite='None', # ТЕПЕРЬ NONE РАЗРЕШЕН!
                secure=True,     # ТЕПЕРЬ SECURE РАБОТАЕТ!
                path='/'
            )
            # Удаляем его из JSON ответа для безопасности
            del response.data['refresh']
            
        return response

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        response = Response({"detail": "Выход выполнен"}, status=status.HTTP_200_OK)
        response.delete_cookie('refresh_token')
        return response
    
class RegisterUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterUserSerializer(data=request.data)
        
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            email = serializer.validated_data.get('email')
            
            # Вызываем бизнес-логику
            user, password = register_new_client(phone_number, email)
            
            return Response({
                "message": "Пользователь успешно зарегистрирован. Пароль отправлен по SMS.",
                "debug_password": password 
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserViewSet(viewsets.ModelViewSet):
    # Базовый ViewSet для обычных пользователей / клиентов
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)
        return queryset


class AdminViewSet(viewsets.ModelViewSet):
    # ViewSet для управления администраторами филиалов
    queryset = User.objects.filter(role='branch_admin')
    serializer_class = AdminSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset

    def create(self, request, *args, **kwargs):
        if getattr(request.user, 'role', '') != 'main_admin':
            return Response(
                {"detail": "У вас нет прав для создания администраторов."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save(role='branch_admin')
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ManagerViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(role='manager')
    serializer_class = ManagerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Получаем ID из параметров URL (?branch=1)
        branch_id = self.request.query_params.get('branch')
        
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        elif getattr(self.request.user, 'role', '') in ['branch_admin', 'branchadmin']:
            queryset = queryset.filter(branch_id=self.request.user.branch_id)
            
        return queryset

    def create(self, request, *args, **kwargs):
        if getattr(request.user, 'role', '') not in ['main_admin', 'mainadmin', 'branch_admin', 'branchadmin']:
            return Response({"detail": "Нет прав для создания менеджеров"}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        
        if getattr(request.user, 'role', '') in ['branch_admin', 'branchadmin']:
            data['branch'] = request.user.branch_id
            
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        departments_data = serializer.validated_data.pop('departments', [])
        password = serializer.validated_data.pop('password', None)
        
        user = serializer.save(role='manager')
        
        if password:
            user.set_password(password)
            user.save()

        if departments_data:
            user.departments.set(departments_data)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object() # get_object автоматически проверяет, принадлежит ли оно юзеру из get_queryset
        
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            
        return Response({'status': 'Уведомление прочитано'}, status=status.HTTP_200_OK)

    # detail=False означает, что ID не нужен (например, /api/notifications/mark_all_as_read/)
    @action(detail=False, methods=['patch'])
    def mark_all_as_read(self, request):
        # Получаем все непрочитанные уведомления текущего пользователя
        unread_notifications = self.get_queryset().filter(is_read=False)
        
        updated_count = unread_notifications.update(is_read=True)
        
        return Response({
            'status': 'Все уведомления прочитаны',
            'updated_count': updated_count
        }, status=status.HTTP_200_OK)
    
class CarViewSet(viewsets.ModelViewSet):
    serializer_class = CarSerializer
    permission_classes = [permissions.IsAuthenticated]

    # Пользователь должен видеть только СВОИ машины
    def get_queryset(self):
        return Car.objects.filter(owner=self.request.user)
    
class MainAdminContactView(APIView):
    # Разрешаем доступ всем пользователям (даже неавторизованным)
    permission_classes = [AllowAny]

    def get(self, request):
        # Ищем первого попавшегося пользователя с ролью Главного администратора
        main_admin = User.objects.filter(role=User.Roles.MAIN_ADMIN).first()
        
        if main_admin and main_admin.email:
            return Response({"email": main_admin.email})
        
        # Если админа в базе пока нет, возвращаем дефолтную почту
        return Response({"email": "admin@carservice.ru"})