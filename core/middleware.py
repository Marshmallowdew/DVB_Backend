# core/middleware.py (или users/middleware.py)
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from urllib.parse import parse_qs

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    try:
        # Расшифровываем токен. В SimpleJWT id пользователя обычно лежит в ключе 'user_id'
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get('user_id')
        if user_id:
            return User.objects.get(id=user_id)
        return AnonymousUser()
    except Exception as e:
        # Ловим абсолютно все ошибки (истек токен, неверный формат и т.д.)
        print(f"WebSocket Auth Error: {e}")
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        
        token = query_params.get("token", [None])[0]
        
        if token:
            # Получаем пользователя
            user = await get_user_from_token(token)
            scope["user"] = user
        else:
            scope["user"] = AnonymousUser()
            
        return await super().__call__(scope, receive, send)
