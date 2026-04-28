from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Order
from .models import Box
from .models import Mechanic
from services.serializers import ServiceSerializer, MechanicSerializer

class BoxSerializerShort(serializers.ModelSerializer):
    class Meta:
        model = Box
        fields = ('id', 'name')

class OrderReadSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    mechanic = MechanicSerializer(read_only=True)
    box = BoxSerializerShort(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    
    # Это телефон и ФИО клиента
    client_phone = serializers.CharField(source='client.phone_number', read_only=True)
    client_email = serializers.EmailField(source='client.email', read_only=True)
    client_first_name = serializers.CharField(source='client.first_name', read_only=True)
    client_last_name = serializers.CharField(source='client.last_name', read_only=True)
    
    class Meta:
        model = Order
        fields = (
            'id', 'client', 'client_phone', 'client_first_name', 'client_last_name', 'client_email',
            'phone_number', # <--- ОБЯЗАТЕЛЬНО ДОБАВЬТЕ ЭТО ПОЛЕ СЮДА (телефон гостя, сохраненный в самом заказе)
            'branch', 'branch_name', 'service', 'mechanic', 'box', 
            'duration_minutes', 'car_brand', 'car_model', 'car_number', 'car_vin',
            'appointment_time', 'status', 'status_display', 'client_comment', 
            'admin_comment', 'created_at', 'total_price',
            'linking_pin'
        )

class OrderCreateSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True, write_only=True)
    client_first_name = serializers.CharField(max_length=50, required=False, allow_blank=True, write_only=True)
    
    class Meta:
        model = Order
        fields = (
            'id', 'branch', 'service', 'mechanic', 'appointment_time', 
            'car_brand', 'car_model', 'car_number', 'car_vin',
            'client_comment', 'phone_number', 'client_first_name'
        )

    def validate(self, attrs):
        branch = attrs.get('branch')
        service = attrs.get('service')
        mechanic = attrs.get('mechanic')
        appointment_time = attrs.get('appointment_time')

        if service.branch != branch:
            raise serializers.ValidationError({"service": "Эта услуга не предоставляется в выбранном филиале."})
        
        if mechanic and mechanic.branch != branch:
            raise serializers.ValidationError({"mechanic": "Этот мастер не работает в выбранном филиале."})

        if appointment_time and appointment_time < timezone.now():
            raise serializers.ValidationError({"appointment_time": "Нельзя записаться на прошедшее время."})

        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Вы должны быть авторизованы для создания записи.")

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user

        guest_phone = validated_data.pop('phone_number', '')
        guest_name = validated_data.pop('client_first_name', '').strip()
        
        def normalize_phone(phone_str):
            import re
            # Оставляем только цифры
            digits = re.sub(r'\D', '', phone_str)
            if not digits:
                return ''
            # Если 11 цифр и начинается с 8, меняем 8 на 7
            if len(digits) == 11 and digits.startswith('8'):
                return '7' + digits[1:]
            # Если 10 цифр, просто подставляем 7 спереди
            if len(digits) == 10:
                return '7' + digits
            return digits
        
        # Нормализуем телефон гостя
        normalized_guest_phone = normalize_phone(guest_phone)
        
        explicit_client_id = self.initial_data.get('client') or self.initial_data.get('client_id')

        if explicit_client_id:
            validated_data['client_id'] = explicit_client_id
            validated_data['is_linked'] = True
        elif normalized_guest_phone:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            existing_user = None
            users_with_phones = User.objects.exclude(phone_number__isnull=True).exclude(phone_number='')
            
            for u in users_with_phones:
                # Нормализуем номер из базы тем же алгоритмом
                normalized_db_phone = normalize_phone(str(u.phone_number))
                
                # Сравниваем полностью нормализованные номера (или хотя бы последние 10 цифр)
                if normalized_guest_phone[-10:] == normalized_db_phone[-10:]:
                    existing_user = u
                    break
            
            if existing_user:
                validated_data['client'] = existing_user
                validated_data['is_linked'] = True
            else:
                validated_data['client'] = None
                validated_data['is_linked'] = False
                
                # СОХРАНЯЕМ В БАЗУ НОРМАЛИЗОВАННЫЙ НОМЕР 
                validated_data['phone_number'] = normalized_guest_phone
                
                if guest_name:
                    existing_comment = validated_data.get('client_comment', '')
                    validated_data['client_comment'] = f"Имя клиента: {guest_name}\n{existing_comment}".strip()
        else:
            validated_data['client'] = user
            validated_data['phone_number'] = getattr(user, 'phone_number', '')
            validated_data['is_linked'] = True


        service = validated_data.get('service')
        appointment_time = validated_data.get('appointment_time')
        duration = service.duration_minutes
        end_time = appointment_time + timedelta(minutes=duration)
        department = service.department
        branch = service.branch

        start_of_day = appointment_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        daily_orders = Order.objects.filter(
            branch=branch,
            appointment_time__gte=start_of_day,
            appointment_time__lt=end_of_day
        ).exclude(status__in=['cancelled', 'completed']).select_related('service')

        overlapping_orders = []
        for order in daily_orders:
            o_start = order.appointment_time
            o_duration = getattr(order, 'duration_minutes', order.service.duration_minutes)
            o_end = o_start + timedelta(minutes=o_duration)
            if o_start < end_time and o_end > appointment_time:
                overlapping_orders.append(order)

        suitable_boxes = Box.objects.filter(branch=branch, is_active=True, departments=department)
        busy_box_ids = [order.box.id for order in overlapping_orders if order.box is not None]
        available_box = suitable_boxes.exclude(id__in=busy_box_ids).first()
        
        if not available_box:
            raise serializers.ValidationError({"appointment_time": "На это время нет свободных боксов."})
            
        validated_data['box'] = available_box
        
        requested_mechanic = validated_data.get('mechanic')
        busy_mechanic_ids = [order.mechanic.id for order in overlapping_orders if order.mechanic is not None]

        suitable_mechanics = Mechanic.objects.filter(branch=branch, is_active=True, departments=department)
        available_mechanic = suitable_mechanics.exclude(id__in=busy_mechanic_ids).first()
        
        if not available_mechanic:
            raise serializers.ValidationError({"appointment_time": "На это время нет свободных мастеров."})
            
        validated_data['mechanic'] = available_mechanic
        validated_data['duration_minutes'] = duration

        return super().create(validated_data)
    
class OrderUpdateSerializer(serializers.ModelSerializer):
    # Сериализатор для обновления заказа администратором
    class Meta:
        model = Order
        fields = ('status', 'admin_comment')
