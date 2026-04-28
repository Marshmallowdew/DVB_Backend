from rest_framework import serializers
from .models import Service, Mechanic

class ServiceSerializer(serializers.ModelSerializer):
    # Сериализатор для вывода информации об услуге
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = Service
        fields = ('id', 'name', 'description', 'price', 'duration_minutes', 'branch', 'branch_name', 'department')


class MechanicSerializer(serializers.ModelSerializer):
    # Сериализатор для вывода информации о мастере
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    full_name = serializers.SerializerMethodField()
    department_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Mechanic
        fields = ('id', 'first_name', 'last_name', 'full_name', 'departments', 'department_names',
                   'experience_years', 'branch', 'branch_name')
        
    def get_department_names(self, obj):
        return [dept.name for dept in obj.departments.all()]
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
