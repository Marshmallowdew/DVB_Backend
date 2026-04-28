import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        
        # Если пользователя нет или он не авторизован - закрываем сокет
        if not self.user or self.user.is_anonymous:
            await self.close()
            return
            
        self.group_name = f"user_{self.user.id}"

        # Подключаем канал к группе пользователя
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification', 
            'id': event.get('notification_id'),
            'message': event.get('message', ''),
            'created_at': event.get('created_at', ''),
            'is_read': False
        }))
