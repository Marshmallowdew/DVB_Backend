from django.contrib import admin
from .models import Service, Mechanic

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'price', 'duration_minutes', 'is_active')
    list_filter = ('branch', 'is_active')
    search_fields = ('name', 'branch__name')
    list_editable = ('price', 'is_active')

@admin.register(Mechanic)
class MechanicAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'get_departments', 'branch', 'is_active')
    list_filter = ('branch', 'is_active')
    search_fields = ('first_name', 'last_name', 'get_departments')

    def get_departments(self, obj):
        return ", ".join([d.name for d in obj.departments.all()])
    
    get_departments.short_description = 'Отделы (Специализации)'
