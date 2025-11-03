from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsuarioViewSet, MototaxiViewSet, ViajeViewSet, PagoViewSet
from .views import MototaxiViewSet
from .views import RegistroUsuarioAPIView
from .views import UsuarioActualAPIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register('usuarios', UsuarioViewSet)
router.register('mototaxis', MototaxiViewSet)
router.register('viajes', ViajeViewSet)
router.register('pagos', PagoViewSet)

urlpatterns = [
    path('usuario/', UsuarioActualAPIView.as_view(), name='usuario_actual'),

    # Registro de usuarios
    path('registro/', RegistroUsuarioAPIView.as_view(), name='registro'),

    # Autenticación JWT
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Endpoints del sistema
    path('', include(router.urls)),
]
