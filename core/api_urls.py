from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from services.views import ServiceViewSet, MechanicViewSet
from orders.views import OrderViewSet, AvailableSlotsView
from branches.views import BranchViewSet, DepartmentViewSet, BoxViewSet, StatisticsView
from users.views import AdminViewSet, ManagerViewSet, NotificationViewSet, CarViewSet

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'mechanics', MechanicViewSet, basename='mechanic')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'branches', BranchViewSet, basename='branch')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'boxes', BoxViewSet, basename='box')
router.register(r'admins', AdminViewSet, basename='admin')
router.register(r'managers', ManagerViewSet, basename='manager')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'cars', CarViewSet, basename='car')

urlpatterns = [
    # ДОБАВЛЯЕМ ПУТЬ ДЛЯ ОБНОВЛЕНИЯ ТОКЕНА (откликнется на /api/token/refresh/)
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Все пути, начинающиеся с /api/users/ пойдут в users.urls
    path('users/', include('users.urls')),
    
    path('orders/available-slots/', AvailableSlotsView.as_view(), name='available-slots'),
    
    path('statistics/', StatisticsView.as_view(), name='statistics'),
    # Роутер должен быть в самом конце
    path('', include(router.urls)),
]
