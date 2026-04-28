from rest_framework import serializers
from .models import Branch, Department, Box
from users.services import normalize_phone_number

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = (
            'id', 'name', 'address', 'phone_number', 'phone_number_2', 
            'opening_time', 'closing_time', 'is_active'
        )

    def validate_phone_number(self, value):
        if value:
            try:
                return normalize_phone_number(value)
            except ValueError as e:
                raise serializers.ValidationError(str(e))
        return value

    # Валидация для второго номера
    def validate_phone_number_2(self, value):
        if value:
            try:
                return normalize_phone_number(value)
            except ValueError as e:
                raise serializers.ValidationError(str(e))
        return value

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class BoxSerializer(serializers.ModelSerializer):
    department_names = serializers.SerializerMethodField()

    class Meta:
        model = Box
        fields = ['id', 'name', 'branch', 'departments', 'department_names', 'is_active']

    def get_department_names(self, obj):
        return [dept.name for dept in obj.departments.all()]