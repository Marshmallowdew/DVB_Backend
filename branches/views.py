from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.db.models import Count, Avg
from django.db.models.functions import ExtractHour
from django.utils.dateparse import parse_date


from .models import Branch, Department, Box
from orders.models import Order
from branches.serializers import BranchSerializer, DepartmentSerializer, BoxSerializer

class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.filter(is_active=True)
    serializer_class = BranchSerializer
    permission_classes = [AllowAny]

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        branch_id = self.request.query_params.get('branch')
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        
        if self.request.user.is_authenticated and hasattr(self.request.user, 'role'):
            if self.request.user.role == 'branch_admin' and self.request.user.branch_id:
                queryset = queryset.filter(branch_id=self.request.user.branch_id)
            
        return queryset
    
class BoxViewSet(viewsets.ModelViewSet):
    queryset = Box.objects.all()
    serializer_class = BoxSerializer
    permission_classes = [IsAuthenticatedOrReadOnly] # Гости могут читать, админы создавать

    def get_queryset(self):
        queryset = super().get_queryset()
        branch_id = self.request.query_params.get('branch')
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
            
        # Фильтр для админов филиала
        if self.request.user.is_authenticated and hasattr(self.request.user, 'role'):
            if self.request.user.role == 'branch_admin' and self.request.user.branch_id:
                queryset = queryset.filter(branch_id=self.request.user.branch_id)
                
        return queryset

class StatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Только админы могут смотреть статистику
        if request.user.role not in ['main_admin', 'mainadmin', 'branch_admin', 'branchadmin']:
            return Response({"detail": "Нет прав доступа"}, status=403)

        branch_id = request.query_params.get('branch_id')
        
        # Получаем даты из параметров запроса
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Базовый QuerySet
        queryset = Order.objects.all()

        # Фильтрация по филиалу
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        elif request.user.role in ['branch_admin', 'branchadmin']:
            queryset = queryset.filter(branch_id=request.user.branch_id)

        # фильтр по датам
        if start_date:
            parsed_start = parse_date(start_date)
            if parsed_start:
                queryset = queryset.filter(appointment_time__date__gte=parsed_start)
            
        if end_date:
            parsed_end = parse_date(end_date)
            if parsed_end:
                queryset = queryset.filter(appointment_time__date__lte=parsed_end)

        # 1. Общее количество заказов
        total_orders = queryset.count()

        # 2. Средний чек
        average_check = 0
  
        if hasattr(Order, 'total_price'):
            avg_check_data = queryset.filter(total_price__isnull=False).aggregate(avg_price=Avg('total_price'))
            if avg_check_data['avg_price']:
                average_check = round(avg_check_data['avg_price'], 2)

        # 3. Топ популярных услуг
        popular_services = queryset.values(
            'service__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        # 4. Популярное время записи
        popular_times = queryset.annotate(
            hour=ExtractHour('appointment_time')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')

        return Response({
            'total_orders': total_orders,
            'average_check': average_check, 
            'popular_services': list(popular_services),
            'popular_times': list(popular_times)
        })