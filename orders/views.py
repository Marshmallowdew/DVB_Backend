import zoneinfo
import logging

from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from django.utils.dateparse import parse_date
from django.utils import timezone
from datetime import datetime, timedelta, time

from django_filters.rest_framework import DjangoFilterBackend

from .models import Service, Box, Order, Mechanic
from .serializers import OrderReadSerializer, OrderCreateSerializer, OrderUpdateSerializer
from core.permissions import IsAdminOrManager

logger = logging.getLogger('orders_logger')

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrManager]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # 2. Поля для точной фильтрации
    filterset_fields = ['status', 'branch', 'mechanic']
    
    # 3. ПОЛЯ ДЛЯ ПОИСКА
    search_fields = [
        'client__phone_number', 
        'client__first_name', 
        'client__last_name', 
        'client__email',
        'car_brand', 
        'car_model', 
        'car_number', 
        'car_vin'
    ]
    
    # 4. ПОЛЯ ДЛЯ СОРТИРОВКИ
    ordering_fields = ['appointment_time', 'created_at', 'id']
    ordering = ['-appointment_time']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Order.objects.none()
            
        # 1. Главный админ видит всё
        if user.role == 'main_admin':
            return Order.objects.all()
            
        # 2. Админ филиала видит все заказы своего филиала
        elif user.role == 'branch_admin' and user.branch_id:
            return Order.objects.filter(service__department__branch_id=user.branch_id)
            
        # 3. Менеджер видит только заказы тех ОТДЕЛОВ, к которым он прикреплен
        elif user.role == 'manager':
            manager_departments = user.departments.all()
            return Order.objects.filter(service__department__in=manager_departments)
            
        # 4. Клиент видит свои заказы
        return Order.objects.filter(client=user)

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return OrderUpdateSerializer
        return OrderReadSerializer

    def perform_create(self, serializer):
        service = serializer.validated_data.get('service')
        service_price = service.price if hasattr(service, 'price') else 0
        
        # Сохраняем заказ
        order = serializer.save(total_price=service_price)

        # Если заказ создали для непривязанного клиента (по телефону), генерируем PIN
        order.generate_linking_pin()
        
        try:
            # Кто создал заказ (сам клиент или менеджер)
            creator = self.request.user.email if (self.request and self.request.user.is_authenticated) else 'Система'
            
            # Чей это заказ
            client_info = order.client.email if order.client else f"Гость ({order.phone_number})"
            
            service_name = order.service.name if order.service else 'Услуга удалена'
            app_time = order.appointment_time.strftime('%d.%m.%Y %H:%M')
            
            log_message = (
                f"ЗАКАЗ #{order.id} | "
                f"Создал: {creator} | "
                f"Клиент: {client_info} | "
                f"Услуга: {service_name} | "
                f"Авто: {order.car_brand} {order.car_model} ({order.car_number}) | "
                f"Дата визита: {app_time}"
            )
            
            # Пишем в файл
            logger.info(log_message)
        except Exception as e:
            # Если при формировании текста для лога что-то пошло не так, 
            # мы не хотим, чтобы заказ отвалился с 500 ошибкой.
            logger.error(f"Ошибка при логировании заказа #{order.id}: {str(e)}")

    def perform_update(self, serializer):
        old_order = self.get_object()
        
        updated_order = serializer.save()
        
        if old_order.status == 'pending' and updated_order.status == 'confirmed':
            self._send_confirmation_notification(updated_order)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='cancel')
    def cancel_order(self, request, pk=None):
        order = self.get_object()
        
        # Разрешаем отменять только если клиент - это владелец заказа
        if order.client != request.user:
            return Response({"error": "Вы не можете отменить чужой заказ"}, status=status.HTTP_403_FORBIDDEN)
            
        if order.status not in ['pending', 'confirmed']:
            return Response({"error": "Заказ уже в работе или отменен"}, status=status.HTTP_400_BAD_REQUEST)
            
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        return Response({"message": "Заказ успешно отменен"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='link-account')
    def link_account(self, request):
        """
        Эндпоинт для привязки гостевых заказов к аккаунту клиента
        по номеру телефона и PIN-коду с чека.
        """
        user = request.user
        
        # Проверяем, что запрос делает авторизованный клиент
        if not user.is_authenticated:
            return Response(
                {"error": "Для привязки заказов необходимо войти в аккаунт."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        phone_number = request.data.get('phone_number')
        pin_code = request.data.get('pin_code')

        if not phone_number or not pin_code:
            return Response(
                {"error": "Необходимо указать номер телефона и PIN-код."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        import re
        digits = re.sub(r'\D', '', phone_number)
        
        if len(digits) == 11 and digits.startswith('8'):
            normalized_phone = '7' + digits[1:]
        elif len(digits) == 10:
            normalized_phone = '7' + digits
        else:
            normalized_phone = digits

        # 1. Ищем заказ, который соответствует нормализованному телефону и ПИН-коду
        valid_order = Order.objects.filter(
            phone_number=normalized_phone,
            linking_pin=pin_code,
            is_linked=False
        ).first()

        # Если такого заказа нет или ПИН-код введен неверно
        if not valid_order:
            return Response(
                {"error": "Неверный номер телефона или PIN-код, либо заказ уже привязан."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Проверяем срок действия ПИН-кода
        if valid_order.pin_expires_at and valid_order.pin_expires_at < timezone.now():
            return Response(
                {"error": "Срок действия PIN-кода истек. Запросите новый код у менеджера при следующем визите."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Находим ВСЕ непривязанные заказы с этим номером телефона
        unlinked_orders = Order.objects.filter(
            phone_number=normalized_phone,
            is_linked=False
        )
        
        linked_count = unlinked_orders.count()

        # 4. Привязываем заказы к текущему пользователю и "сжигаем" PIN-код
        unlinked_orders.update(
            client=user,
            is_linked=True,
            linking_pin=None,
            pin_expires_at=None
        )

        # 5. если у клиента в профиле еще не был заполнен телефон, заполняем его
        if not user.phone_number:
            user.phone_number = normalized_phone
            user.save(update_fields=['phone_number'])

        return Response({
            "message": f"Успешно привязано заказов: {linked_count}",
            "linked_count": linked_count
        }, status=status.HTTP_200_OK)


class AvailableSlotsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        service_id = request.query_params.get('service_id') or request.query_params.get('service')
        date_str = request.query_params.get('date')

        if not service_id or not date_str:
            return Response({"error": "Требуются параметры service_id и date"}, status=400)

        target_date = parse_date(date_str)
        if not target_date:
            return Response({"error": "Неверный формат даты"}, status=400)

        try:
            # Сразу подтягиваем branch, чтобы не делать лишний запрос
            service = Service.objects.select_related('branch').get(id=service_id)
        except Service.DoesNotExist:
            return Response({"error": "Услуга не найдена"}, status=404)

        branch = service.branch
        department = service.department
        duration = service.duration_minutes

        local_tz = zoneinfo.ZoneInfo("Europe/Moscow")

        # Ищем подходящие ресурсы (боксы и механиков)
        suitable_boxes = set(Box.objects.filter(
            branch=branch, is_active=True, departments=department
        ).values_list('id', flat=True))
        
        suitable_mechanics = set(Mechanic.objects.filter(
            branch=branch, is_active=True, departments=department
        ).values_list('id', flat=True))

        if not suitable_boxes or not suitable_mechanics:
            return Response({"slots": []})

        # Если поля не существуют, используем дефолтные 09:00 - 20:00
        open_time = getattr(branch, 'opening_time', time(9, 0))
        close_time = getattr(branch, 'closing_time', time(20, 0))

        start_of_day = datetime.combine(target_date, open_time, tzinfo=local_tz)
        end_of_day = datetime.combine(target_date, close_time, tzinfo=local_tz)

        # Выбираем только те заказы, которые пересекаются с рабочим временем
        existing_orders = Order.objects.filter(
            branch=branch,
            appointment_time__gte=start_of_day,
            appointment_time__lte=end_of_day
        ).exclude(status__in=['cancelled', 'completed']).select_related('service')

        booked_intervals = []
        for order in existing_orders:
            order_start = order.appointment_time
            order_duration = getattr(order, 'duration_minutes', order.service.duration_minutes)
            order_end = order_start + timedelta(minutes=order_duration)
            
            booked_intervals.append({
                'start': order_start,
                'end': order_end,
                'box_id': order.box_id,
                'mechanic_id': order.mechanic_id
            })

        now = timezone.now()
        available_slots = []
        step = timedelta(minutes=30)
        
        current_dt = start_of_day

        # Итерируемся с шагом 30 минут, пока слот помещается в рабочее время
        while current_dt + timedelta(minutes=duration) <= end_of_day:
            
            # Если слот в прошлом или начнется меньше чем через 30 минут — пропускаем
            if current_dt < now + timedelta(minutes=30):
                current_dt += step
                continue

            slot_start = current_dt
            slot_end = current_dt + timedelta(minutes=duration)

            busy_boxes = set()
            busy_mechanics = set()

            for interval in booked_intervals:
                # Проверка пересечения отрезков времени
                if slot_start < interval['end'] and slot_end > interval['start']:
                    if interval['box_id']:
                        busy_boxes.add(interval['box_id'])
                    if interval['mechanic_id']:
                        busy_mechanics.add(interval['mechanic_id'])

            # Проверяем, есть ли хотя бы один свободный бокс и механик
            has_free_box = any(b_id for b_id in suitable_boxes if b_id not in busy_boxes)
            has_free_mechanic = any(m_id for m_id in suitable_mechanics if m_id not in busy_mechanics)

            if has_free_box and has_free_mechanic:
                available_slots.append(slot_start.strftime('%H:%M'))

            current_dt += step

        return Response({"slots": available_slots})