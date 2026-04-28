from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import IsServiceAdminOrReadOnly, IsMechanicManagerOrReadOnly

from .models import Service, Mechanic
from .serializers import ServiceSerializer, MechanicSerializer

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [IsServiceAdminOrReadOnly] 
    
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['branch']

    def get_queryset(self):
        user = self.request.user
        queryset = Service.objects.all()

        if not user.is_authenticated or user.role == 'user':
            return queryset

        # Если это админ филиала, он видит и управляет только услугами филиала
        if user.role == 'branch_admin':
            if user.branch_id:
                return queryset.filter(branch_id=user.branch_id)
            return Service.objects.none()

        return queryset

class MechanicViewSet(viewsets.ModelViewSet):
    serializer_class = MechanicSerializer
    permission_classes = [IsMechanicManagerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['branch']

    def get_queryset(self):
        user = self.request.user
        
        # Если пользователь не авторизован - отдаем пустой список
        if not user.is_authenticated:
            return Mechanic.objects.none()

        # Базовый QuerySet (показываем только активных мастеров, если не требуется иное)
        qs = Mechanic.objects.filter(is_active=True)

        # 1. Главный админ видит всех мастеров
        if user.role in ['main_admin', 'mainadmin']:
            return qs

        # 2. Админ филиала видит мастеров только своего филиала
        elif user.role in ['branch_admin', 'branchadmin'] and user.branch_id:
            return qs.filter(branch_id=user.branch_id)

        # 3. Менеджер видит мастеров своего своих отделов
        elif user.role == 'manager':
            # Если менеджер должен видеть ВСЕХ мастеров филиала:
            # return qs.filter(branch_id=user.branch_id)
            
            # Если менеджер должен видеть ТОЛЬКО мастеров своих отделов:
            manager_departments = user.departments.all()
            return qs.filter(departments__in=manager_departments).distinct()

        return qs
