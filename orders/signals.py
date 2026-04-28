import threading
from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model

from orders.models import Order
from users.models import Notification

User = get_user_model()

# Функция отправки почты в фоне
def send_status_email_in_background(client_email, order_id, status_display, branch_name):
    subject = f"Обновление статуса заказа #{order_id}"
    message = f"""
Здравствуйте!
    
Статус вашего заказа #{order_id} (Филиал: {branch_name}) был изменён.
Новый статус: {status_display}.
    
Спасибо, что пользуетесь нашими услугами!
"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[client_email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Ошибка при отправке письма: {e}")


@receiver(pre_save, sender=Order)
def order_status_changed(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_order = Order.objects.get(pk=instance.pk)
        except Order.DoesNotExist:
            return
            
        if old_order.status != instance.status:
            client = instance.client if hasattr(instance, 'client') else None
            
            if client:
                raw_status = instance.get_status_display() if hasattr(instance, 'get_status_display') else instance.status
                status_display = str(raw_status)
                
                message = f"Статус вашего заказа изменен на '{status_display}'"
                
                # Сохраняем в БД
                notif = Notification.objects.create(
                    user=client,
                    order=instance,
                    message=message
                )
                
                # Отправляем в WS
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'user_{client.id}',
                        {
                            'type': 'send_notification',
                            'notification_id': notif.id,
                            'message': notif.message,
                            'created_at': str(notif.created_at)
                        }
                    )
                except Exception as e:
                    print(f"WS Send Error (Client): {e}")
                
                # Отправляем письмо
                if client.email:
                    branch_name = instance.branch.name if hasattr(instance, 'branch') and instance.branch else 'Неизвестный филиал'
                    email_thread = threading.Thread(
                        target=send_status_email_in_background,
                        args=(client.email, instance.id, status_display, branch_name)
                    )
                    email_thread.start()


@receiver(post_save, sender=Order)
def notify_admins_and_managers(sender, instance, created, **kwargs):
    if not created:
        return

    channel_layer = get_channel_layer()
    
    # Уведомляем Админов
    admins = User.objects.filter(role__in=['main_admin', 'branch_admin'])
    for admin in admins:
        branch_name = instance.branch.name if hasattr(instance, 'branch') and instance.branch else 'Неизвестный филиал'
        
        notif = Notification.objects.create(
            user=admin,
            order=instance,
            message=f"Новый заказ-наряд #{instance.id} (Филиал: {branch_name})"
        )
        try:
            async_to_sync(channel_layer.group_send)(
                f"user_{admin.id}",
                {
                    "type": "send_notification",
                    "notification_id": notif.id,
                    "message": notif.message,
                    "created_at": str(notif.created_at)
                }
            )
        except Exception as e:
            print(f"WS Send Error (Admin): {e}")

    # Уведомляем Менеджеров
    if hasattr(instance, 'service') and instance.service and hasattr(instance.service, 'department') and instance.service.department:
        managers = User.objects.filter(
            role='manager',
            branch=instance.branch,
            departments=instance.service.department
        )
        for manager in managers:
            notif = Notification.objects.create(
                user=manager,
                order=instance,
                message=f"Новый заказ-наряд #{instance.id} в отдел {instance.service.department.name}"
            )
            try:
                async_to_sync(channel_layer.group_send)(
                    f"user_{manager.id}",
                    {
                        "type": "send_notification",
                        "notification_id": notif.id,
                        "message": notif.message,
                        "created_at": str(notif.created_at)
                    }
                )
            except Exception as e:
                print(f"WS Send Error (Manager): {e}")
