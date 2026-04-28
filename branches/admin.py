from django.contrib import admin
from .models import Branch, ServiceAdminProfile, Box

class ServiceAdminProfileInline(admin.StackedInline):
    model = ServiceAdminProfile
    extra = 1

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone_number', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'address')
    inlines = [ServiceAdminProfileInline]

@admin.register(ServiceAdminProfile)
class ServiceAdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'branch', 'assigned_at')
    list_filter = ('branch',)
    search_fields = ('user__phone_number', 'branch__name')

@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'get_departments', 'is_active')
    list_filter = ('branch', 'is_active')

    def get_departments(self, obj):
        return ", ".join([d.name for d in obj.departments.all()])
    get_departments.short_description = 'Отделы'