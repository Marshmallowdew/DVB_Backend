from django.contrib import admin
from django.contrib.auth.models import Group
from .models import User

admin.site.unregister(Group)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'email', 'get_full_name_custom', 'role', 'is_phone_verified', 'is_active')
    list_filter = ('role', 'is_phone_verified', 'is_active', 'is_staff')
    search_fields = ('phone_number', 'email', 'first_name', 'last_name', 'middle_name')
    ordering = ('-date_joined',)
    
    # Настройка полей при редактировании пользователя
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Персональная информация', {'fields': ('last_name', 'first_name', 'middle_name', 'email')}),
        ('Права доступа', {'fields': ('role', 'is_phone_verified', 'is_active', 'is_staff', 'is_superuser')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    

    def get_full_name_custom(self, obj):
        # Собираем части имени, игнорируя пустые (None)
        parts = [obj.last_name, obj.first_name, obj.middle_name]
        full_name = " ".join([p for p in parts if p])
        return full_name if full_name else "—"
    
    get_full_name_custom.short_description = 'ФИО'