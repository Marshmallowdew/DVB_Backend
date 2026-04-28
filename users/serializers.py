import re
from users.services import normalize_phone_number
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Notification, Car

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    departments = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'phone_number', 'email', 'first_name', 'last_name', 'middle_name',
        'role', 'branch', 'branch_name', 'departments', 'is_phone_verified', 'old_password', 'new_password')
        read_only_fields = ('id', 'role', 'is_phone_verified')

    def get_departments(self, obj):
        # Проверяем, есть ли у пользователя связь departments
        if hasattr(obj, 'departments') and obj.departments.exists():
            return list(obj.departments.values_list('id', flat=True))
        return []
    
    def validate(self, attrs):
        # Если пытаются сменить пароль, проверяем старый
        if 'new_password' in attrs:
            if 'old_password' not in attrs:
                raise serializers.ValidationError({"old_password": "Для смены пароля введите старый пароль."})
            
            user = self.context['request'].user
            if not user.check_password(attrs['old_password']):
                raise serializers.ValidationError({"old_password": "Старый пароль неверен."})
        return attrs
    
    def validate_phone_number(self, value):
        try:
            return normalize_phone_number(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        
    def update(self, instance, validated_data):

        new_password = validated_data.pop('new_password', None)
        validated_data.pop('old_password', None)
        
        # Обновляем базовые поля (email, имя и тд)
        instance = super().update(instance, validated_data)
        
        # Если есть новый пароль - хэшируем и сохраняем
        if new_password:
            instance.set_password(new_password)
            instance.save()
            
        return instance


class RegisterUserSerializer(serializers.Serializer):
    # Сериализатор для регистрации нового пользователя по номеру телефона
    phone_number = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    def validate_phone_number(self, value):
        try:
            return normalize_phone_number(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    
    def validate(self, attrs):
        # Проверка номера
        phone_number = attrs.get('phone_number')
        if User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError({"phone_number": "Пользователь с таким номером уже существует."})
        return attrs

class ManagerSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    departments = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'first_name', 'last_name', 'middle_name',
            'role', 'email', 'branch', 'branch_name', 'departments', 'password'
        ]
        extra_kwargs = {
            'role': {'default': 'manager'},
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
            'middle_name': {'required': False, 'allow_blank': True},
            'password': {'write_only': True},
        }

    def validate_phone_number(self, value):
        try:
            return normalize_phone_number(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from branches.models import Department
        self.fields['departments'].queryset = Department.objects.all()

    def create(self, validated_data):
        validated_data.pop('password', None)
        
        email = validated_data.pop('email')
        phone_number = validated_data.pop('phone_number')
        
        # Создаем пользователя
        user = User.objects.create_user(
            email=email,
            phone_number=phone_number,
            **validated_data
        )
        
        return user

    def update(self, instance, validated_data):
        departments_data = validated_data.pop('departments', None)
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        # Хэшируем пароль, если он передан
        if password:
            instance.set_password(password)
            
        instance.save()

        # Обновляем отделы
        if departments_data is not None:
            instance.departments.set(departments_data)
            
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if hasattr(instance, 'departments'):
            representation['departments'] = list(instance.departments.values_list('id', flat=True))
        else:
            representation['departments'] = []
        return representation


class AdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'first_name', 'last_name', 'middle_name', 
            'role', 'branch', 'branch_name', 'password', 'email'
        ]
        extra_kwargs = {
            'role': {'default': 'branchadmin'}
        }

    def validate_phone_number(self, value):
        try:
            return normalize_phone_number(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        
    def validate(self, data):
        branch = data.get('branch')
        
        # Если филиал передан, проверяем, есть ли там уже админ
        if branch:
            existing_admins = User.objects.filter(branch=branch, role__in=['branch_admin', 'branchadmin'])
            
            if self.instance:
                existing_admins = existing_admins.exclude(id=self.instance.id)
                
            if existing_admins.exists():
                raise serializers.ValidationError({
                    "branch": "У этого филиала уже есть администратор."
                })
                
        return data
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        
        email = validated_data.pop('email')
        phone_number = validated_data.pop('phone_number')
        
        # Передаем email явным позиционным аргументом
        user = User.objects.create_user(
            email=email, 
            phone_number=phone_number, 
            password=password, 
            **validated_data
        )
            
        return user
    
class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()

class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)

    def validate_email(self, value):
        return value.lower().strip()

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'created_at', 'order']
        read_only_fields = ['id', 'message', 'created_at', 'order']


class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ['id', 'brand', 'model', 'number', 'vin_number']
        read_only_fields = ['id']


    def validate_number(self, value):
        if not value:
            return value 
            
        value = value.upper()
        
        translation_table = str.maketrans('ABEKMHOPCTYX', 'АВЕКМНОРСТУХ')
        value = value.translate(translation_table)

        # 1 буква, 3 цифры, 2 буквы, 2 или 3 цифры региона
        pattern = r'^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}$'
        
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Неверный формат госномера. Ожидается: А123БВ77 или А123БВ777, "
                "используются только буквы А, В, Е, К, М, Н, О, Р, С, Т, У, Х."
            )
            
        return value
    
    # При создании машины мы должны автоматически привязывать её к текущему юзеру
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)