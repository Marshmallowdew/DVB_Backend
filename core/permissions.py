from rest_framework import permissions

class IsMainAdmin(permissions.BasePermission):
   #Доступ только для Главного администратора франшизы
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'main_admin'
        )

class IsServiceAdmin(permissions.BasePermission):
    #Доступ только для Администратора конкретного сервиса
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'service_admin'
        )

class IsServiceAdminOrReadOnly(permissions.BasePermission):
    # Гости и Клиенты могут только смотреть
    def has_permission(self, request, view):
        # Безопасные методы (GET, HEAD, OPTIONS) разрешены всем
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Для изменения данных (POST, PUT, PATCH, DELETE) проверяем роль
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['main_admin', 'branch_admin']
        )

    def has_object_permission(self, request, view, obj):
        # Чтение объекта разрешено всем
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Если пользователь не авторизован - запрещаем
        if not request.user or not request.user.is_authenticated:
            return False

        # Главный админ может редактировать/удалять любой объект
        if request.user.role == 'main_admin':
            return True
            
        # Админ филиала может редактировать/удалять только объекты своего филиала
        if request.user.role == 'branch_admin':
            if hasattr(obj, 'branch_id'):
                return obj.branch_id == request.user.branch_id
            if hasattr(obj, 'branch'):
                return obj.branch == request.user.branch
            
        return False
    
class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Админы и менеджеры могут изменять заказы
        if request.user.role in ['main_admin', 'branch_admin', 'manager']:
            return True
            
        # Клиенты могут создавать заказы (POST)
        if request.user.role == 'user' and request.method == 'POST':
            return True
            
        return False

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Админы
        if request.user.role == 'main_admin':
            return True
            
        if request.user.role == 'branch_admin':
            if hasattr(obj, 'branch_id'):
                return obj.branch_id == request.user.branch_id
            # Если у заказа нет branch_id, проверяем через связанную услугу
            if hasattr(obj, 'service') and obj.service.department:
                return obj.service.department.branch_id == request.user.branch_id
            return False
            
        # Менеджеры
        if request.user.role == 'manager':
            # Запрещаем удаление
            if request.method == 'DELETE':
                return False
            # Разрешаем изменение, только если заказ принадлежит одному из отделов менеджера
            if hasattr(obj, 'service') and obj.service.department:
                return obj.service.department in request.user.departments.all()
            return False
            
        # Обычные клиенты
        if request.user.role == 'user':
            return obj.client == request.user and request.method in permissions.SAFE_METHODS
            
        return False
    
class IsMechanicManagerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Чтение разрешено всем
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Изменение/создание разрешено админам и менеджерам
        if not request.user.is_authenticated:
            return False
            
        return request.user.role in ['main_admin', 'branch_admin', 'manager']