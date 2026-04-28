from django.contrib import admin
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'branch', 'service', 'mechanic', 'appointment_time', 'status')
    list_filter = ('status', 'branch', 'appointment_time')
    search_fields = ('client__phone_number', 'branch__name', 'id')
    date_hierarchy = 'appointment_time'
    list_editable = ('status',)
