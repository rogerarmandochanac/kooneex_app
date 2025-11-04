from rest_framework import viewsets, permissions
from .models import Usuario, Mototaxi, Viaje, Pago
from .serializers import UsuarioSerializer, MototaxiSerializer, ViajeSerializer, PagoSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .permissions import IsAdmin, IsMototaxista, IsPasajero
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from math import radians, cos, sin, asin, sqrt
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

def calcular_distancia(lat1, lon1, lat2, lon2):
    """Calcula la distancia entre dos coordenadas (en kilómetros)."""
    R = 6371  # radio de la Tierra en km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdmin]

class UsuarioActualAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UsuarioSerializer(request.user)
        return Response(serializer.data)

class MototaxiViewSet(viewsets.ModelViewSet):
    queryset = Mototaxi.objects.all()
    serializer_class = MototaxiSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'update', 'partial_update']:
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.rol == 'admin':
            return Mototaxi.objects.all()
        elif user.rol == 'mototaxista':
            return Mototaxi.objects.filter(conductor=user)
        return Mototaxi.objects.none()
    
    @action(detail=False, methods=['post'])
    def actualizar_ubicacion(self, request):
        """Permite al mototaxista actualizar su ubicación actual."""
        user = request.user
        if user.rol != 'mototaxista':
            return Response({'error': 'Solo los mototaxistas pueden actualizar ubicación.'},
                            status=status.HTTP_403_FORBIDDEN)
        lat = request.data.get('latitud')
        lon = request.data.get('longitud')

        if not lat or not lon:
            return Response({'error': 'Debe enviar latitud y longitud.'},
                            status=status.HTTP_400_BAD_REQUEST)

        mototaxi = Mototaxi.objects.get(conductor=user)
        mototaxi.latitud = lat
        mototaxi.longitud = lon
        mototaxi.save()
        return Response({'mensaje': 'Ubicación actualizada correctamente.'})
    
    @action(detail=False, methods=['get'])
    def cercanos(self, request):
        """Devuelve mototaxistas cercanos a una ubicación dada."""
        try:
            lat = float(request.query_params.get('latitud'))
            lon = float(request.query_params.get('longitud'))
        except (TypeError, ValueError):
            return Response({'error': 'Debe proporcionar latitud y longitud válidas.'},
                            status=status.HTTP_400_BAD_REQUEST)

        mototaxis = Mototaxi.objects.filter(disponible=True, latitud__isnull=False, longitud__isnull=False)
        cercanos = []

        for m in mototaxis:
            distancia = calcular_distancia(lat, lon, m.latitud, m.longitud)
            if distancia <= 5:  # en km, puedes ajustar el radio
                data = MototaxiSerializer(m).data
                data['distancia_km'] = round(distancia, 2)
                cercanos.append(data)

        return Response(cercanos)

class ViajeViewSet(viewsets.ModelViewSet):
    queryset = Viaje.objects.all()
    serializer_class = ViajeSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def sugerir_tarifa(self, request, pk=None):
        viaje = self.get_object()
        tarifa = request.data.get('tarifa_sugerida')
        viaje.tarifa_sugerida = tarifa
        viaje.estado = 'negociando'
        viaje.save()
        return Response({'mensaje': 'Tarifa sugerida enviada.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def responder_tarifa(self, request, pk=None):
        viaje = self.get_object()
        decision = request.data.get('decision')  # "aceptar" o "rechazar"

        if decision == 'aceptar':
            viaje.estado = 'aceptado'
            if viaje.tarifa_sugerida is None:
                return Response({"error": "No hay tarifa sugerida para aceptar."}, status=400)
            viaje.tarifa_final = float(viaje.tarifa_sugerida)
            viaje.save()
            return Response({'mensaje': 'Tarifa aceptada.'}, status=status.HTTP_200_OK)
        elif decision == 'rechazar':
            viaje.estado = 'pendiente'
            viaje.tarifa_sugerida = None
            viaje.save()
            return Response({'mensaje': 'Tarifa rechazada, el viaje vuelve a estar disponible.'}, status=status.HTTP_200_OK)

        return Response({'error': 'Decisión inválida.'}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        pasajero = self.request.user
        cantidad = self.request.data.get('cantidad_pasajeros', 1)
        try:
            cantidad = int(cantidad)
        except ValueError:
            cantidad = 1

        # Costo sugerido = 10 pesos por pasajero
        costo_sugerido = cantidad * 10

        serializer.save(pasajero=pasajero, costo_estimado=costo_sugerido)

    
    def perform_update(self, serializer):
        # Si el usuario es mototaxista y cambia estado, se le asigna el viaje
        user = self.request.user
        if user.rol == 'mototaxista' and serializer.validated_data.get('estado') == 'aceptado':
            serializer.save(mototaxista=user)
        else:
            serializer.save()

    def get_queryset(self):
        user = self.request.user
        if user.rol == "mototaxista":
            # Muestra solo viajes pendientes o asignados al mototaxista
            return Viaje.objects.filter(estado__in=["pendiente", "aceptado", "en_curso"]).order_by("-creado_en")
        elif user.rol == "pasajero":
            return Viaje.objects.filter(pasajero=user).order_by("-creado_en")
        return Viaje.objects.none()

    @action(detail=True, methods=['post'])
    def aceptar(self, request, pk=None):
        viaje = self.get_object()
        user = request.user

        if user.rol != "mototaxista":
            return Response({"error": "Solo los mototaxistas pueden aceptar viajes."}, status=status.HTTP_403_FORBIDDEN)

        if viaje.estado != "pendiente":
            return Response({"error": "El viaje ya fue aceptado o no está disponible."}, status=status.HTTP_400_BAD_REQUEST)

        viaje.estado = "aceptado"
        viaje.mototaxista = user
        viaje.save()

        return Response({"mensaje": "Viaje aceptado correctamente.", "viaje_id": viaje.id}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def completar(self, request, pk=None):
        """Permite al mototaxista marcar el viaje como completado."""
        viaje = self.get_object()
        user = request.user

        # if user.rol != "mototaxista":
        #     return Response({"error": "Solo los mototaxistas pueden completar viajes."}, status=status.HTTP_403_FORBIDDEN)

        # if viaje.mototaxista != user:
        #     return Response({"error": "Este viaje no está asignado a ti."}, status=status.HTTP_403_FORBIDDEN)

        if viaje.estado != "en_curso" and viaje.estado != "aceptado":
            return Response({"error": "Solo se pueden completar viajes en curso o aceptados."}, status=status.HTTP_400_BAD_REQUEST)

        if user.rol == 'pasajero':
            viaje.estado = "completado_pasajero"
        
        if user.rol == 'mototaxista':
            viaje.estado = 'completado'

        viaje.save()

        return Response({"mensaje": f"Viaje #{viaje.id} completado correctamente."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def iniciar(self, request, pk=None):
        """Permite al mototaxista iniciar un viaje aceptado."""
        viaje = self.get_object()
        user = request.user

        if user.rol != "mototaxista":
            return Response({"error": "Solo los mototaxistas pueden iniciar un viaje."}, status=status.HTTP_403_FORBIDDEN)

        if viaje.mototaxista != user:
            return Response({"error": "Este viaje no está asignado a ti."}, status=status.HTTP_403_FORBIDDEN)

        if viaje.estado != "aceptado":
            return Response({"error": "Solo los viajes aceptados pueden iniciarse."}, status=status.HTTP_400_BAD_REQUEST)

        viaje.estado = "en_curso"
        viaje.save()

        return Response({"mensaje": f"Viaje #{viaje.id} iniciado correctamente."}, status=status.HTTP_200_OK)

class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer

    def get_queryset(self):
        user = self.request.user
        if user.rol == 'admin':
            return Pago.objects.all()
        elif user.rol == 'pasajero':
            return Pago.objects.filter(viaje__pasajero=user)
        elif user.rol == 'mototaxista':
            return Pago.objects.filter(viaje__mototaxi__conductor=user)
        return Pago.objects.none()



class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Puedes agregar más datos si lo deseas
        token['rol'] = user.rol
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'rol': self.user.rol,
            'telefono': self.user.telefono,
            'direccion': self.user.direccion,
        }
        return data

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

class RegistroUsuarioAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        rol = data.get('rol', 'pasajero')  # por defecto pasajero

        if not username or not password:
            return Response({'error': 'Username y password son obligatorios.'},
                            status=status.HTTP_400_BAD_REQUEST)

        if rol not in ['admin', 'mototaxista', 'pasajero']:
            return Response({'error': 'Rol no válido.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = Usuario.objects.create_user(username=username, email=email, password=password, rol=rol)
        return Response({'mensaje': f'Usuario {username} creado como {rol} correctamente.'},
                        status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer




