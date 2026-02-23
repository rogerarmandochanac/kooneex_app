from .utils import calcular_distancia
from .serializers import (UsuarioSerializer, 
                          MototaxiSerializer, 
                          ViajeSerializer, 
                          PagoSerializer, 
                          OfertaSerializer,
                          UsuarioRegistroSerializer
                        )
from .permissions import IsAdmin
from django.db.models import Prefetch, Exists, OuterRef, Case, When, Value, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone
from .models import (Usuario, 
                     Mototaxi, 
                     Viaje, 
                     Pago, 
                     Oferta
                     )

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from rest_framework.permissions import (IsAuthenticated, 
                                        AllowAny)
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework import (viewsets, 
                            permissions,
                            status,
                            serializers)
from rest_framework.parsers import MultiPartParser, FormParser

from django.db.models import Q

from django.db import transaction

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdmin]

class RegistroUsuarioAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # 🔥 evita CSRF
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = UsuarioRegistroSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"mensaje": "Usuario creado correctamente"},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    
    base_queryset = Viaje.objects.select_related(
        'pasajero', 'mototaxista'
        
    ).prefetch_related(
        Prefetch('ofertas', queryset=Oferta.objects.select_related('mototaxista').only(
            'id', 'monto', 'tiempo_estimado', 'aceptada', 'mototaxista__id', 
            'mototaxista__username',
        ))
    ).only(
        'id', 'estado', 'origen_lat', 'origen_lon', 'destino_lat', 'destino_lon',
        'cantidad_pasajeros', 'costo_estimado', 'costo_final','pasajero__username', 
        'mototaxista__id', 'mototaxista__username', 'referencia', 'distancia_km', 'pasajero__foto'
    )
    
    queryset = base_queryset
    serializer_class = ViajeSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_queryset(self):
        user = self.request.user
        
        if user.rol == 'pasajero':
            return self.base_queryset.filter(pasajero=user).exclude(estado='completado').order_by('-distancia_km')
        
        elif user.rol == 'mototaxista':
            oferta_activa_subquery = Oferta.objects.filter(
                mototaxista=user,
                viaje_id=OuterRef('id'),
                aceptada=True
            ).values('id')
            
            queryset = self.base_queryset.annotate(
                tiene_oferta_activa=Exists(oferta_activa_subquery)
            )
            
            # Si tiene oferta aceptada, mostrar solo ese viaje
            if queryset.filter(tiene_oferta_activa=True, estado__in=['aceptado', 'en_curso']).exists():
                return queryset.filter(tiene_oferta_activa=True, estado__in=['aceptado', 'en_curso'])
            
            # Si no, mostrar viajes pendientes
            return queryset.filter(estado='pendiente').order_by('-distancia_km')
        
        return Viaje.objects.none()
    
    @action(detail=False, methods=['get'])
    def estado_viaje_activo(self, request):
        """Optimizado - una sola consulta"""
        user = request.user
        
        viaje = Viaje.objects.filter(
            pasajero=user,
            estado__in=['pendiente', 'aceptado', 'en_curso']
        ).select_related('mototaxista').only(
            'id', 'estado', 'costo_final',
            'mototaxista__id', 'mototaxista__username'
        ).first()
        
        if not viaje:
            return Response({'estado': None})
        
        return Response({
            'id': viaje.id,
            'estado': viaje.estado,
            'mototaxista': viaje.mototaxista.username if viaje.mototaxista else None,
            'costo_final': float(viaje.costo_final) if viaje.costo_final else None
        })
    
    @action(detail=False, methods=['get'])
    def verificar_viajes_activos(self, request):
        """Versión optimizada"""
        user = request.user
        
        if user.rol == 'pasajero':
            viaje_activo = Viaje.objects.filter(
                pasajero=user,
                estado__in=['aceptado', 'en_curso']
            ).only('id', 'estado').first()
            
            if viaje_activo:
                return Response({
                    'mensaje': 'tiene_viaje_activo', 
                    'estado': viaje_activo.estado,
                    'viaje_id': viaje_activo.id
                }, status=status.HTTP_200_OK)
            
            viaje_pendiente = Viaje.objects.filter(
                pasajero=user,
                estado__in=['pendiente']
            ).only('id', 'estado').first()

            if viaje_pendiente:
                return Response({
                    'mensaje': 'tiene_viaje_pendiente', 
                    'estado': viaje_pendiente.estado,
                    'viaje_id': viaje_pendiente.id
                }, status=status.HTTP_200_OK)

            return Response({'mensaje': 'None'}, status=status.HTTP_204_NO_CONTENT)
        
        elif user.rol == 'mototaxista':
            # Verificar si tiene viaje aceptado o en curso
            viaje_activo = Viaje.objects.filter(
                mototaxista=user,
                estado__in=['aceptado', 'en_curso']
            ).only('id').first()
            
            if viaje_activo:
                if viaje_activo.estado == 'aceptado':
                    return Response({
                        'mensaje': 'tiene_viaje_aceptado',
                        'viaje_id': viaje_activo.id
                    }, status=status.HTTP_200_OK)
                
                elif viaje_activo.estado == 'en_curso':
                    return Response({
                        'mensaje': 'tiene_viaje_en_curso',
                        'viaje_id': viaje_activo.id
                    }, status=status.HTTP_200_OK)
            
            # Verificar si tiene oferta pendiente
            oferta_pendiente = Oferta.objects.filter(
                mototaxista=user,
                aceptada=False,
                viaje__estado='pendiente'
            ).select_related('viaje', 'viaje__pasajero').only('viaje_id').first()
            
            if oferta_pendiente:
                return Response({
                    'mensaje': 'tiene_viaje_ofertado',
                    'viaje_id': oferta_pendiente.viaje.id
                }, status=status.HTTP_200_OK)
            
            else:
                return Response({
                    'mensaje':'None',
                }, status=status.HTTP_200_OK)
        
        return Response({'mensaje': 'None'}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def aceptar(self, request, pk=None):
        viaje = self.get_object()
        user = request.user

        if user.rol != "mototaxista":
            return Response(
                {"error": "Solo los mototaxistas pueden aceptar viajes."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            viaje.aceptar(user)
            return Response({
                "mensaje": "Viaje aceptado correctamente.",
                "viaje_id": viaje.id
            })
        
        except ValidationError as e:
            return Response(
                {"error": e.message},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['delete'])
    def eliminar(self, request, pk=None):
        viaje = self.get_object()
        user = request.user

        # Seguridad extra (opcional pero recomendado)
        if user != viaje.pasajero and user.rol != 'admin':
            return Response(
                {"error": "No tienes permiso para eliminar este viaje."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            viaje.eliminar()
        except ValidationError as e:
            return Response(
                {"error": e.message},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"mensaje": "Viaje eliminado correctamente."},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['patch'])
    def completar(self, request, pk=None):
        """Completar viaje - optimizado"""
        with transaction.atomic():
            viaje = self.get_object()
            user = request.user

            if viaje.estado not in ["en_curso", "aceptado"]:
                return Response(
                    {"error": "Solo se pueden completar viajes en curso o aceptados."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            viaje.estado = 'completado'
            viaje.save()

            # Si el usuario es mototaxista, liberar su disponibilidad
            if user.rol == 'mototaxista' and viaje.mototaxista == user:
                try:
                    mototaxi = Mototaxi.objects.get(conductor=user)
                    mototaxi.disponible = True
                    mototaxi.save()
                except Mototaxi.DoesNotExist:
                    pass

            # Crear registro de pago automáticamente
            if viaje.costo_final:
                Pago.objects.get_or_create(
                    viaje=viaje,
                    defaults={
                        'monto': viaje.costo_final,
                        'metodo': 'efectivo'
                    }
                )

            return Response({
                "mensaje": f"Viaje #{viaje.id} completado correctamente."
            }, status=status.HTTP_200_OK)
    
class OfertaViewSet(viewsets.ModelViewSet):
    queryset = Oferta.objects.select_related(
        'viaje', 'mototaxista', 'viaje__pasajero'
    ).only(
        'id', 'monto', 'tiempo_estimado', 'aceptada', 'creada_en',
        'viaje__id', 'viaje__estado', 'viaje__costo_final', 'viaje__cantidad_pasajeros',
        'mototaxista__id', 'mototaxista__username',
        'mototaxista__first_name', 'mototaxista__last_name',
        'viaje__pasajero__id', 'viaje__pasajero__username', 'mototaxista__foto'
    )
    serializer_class = OfertaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.rol == "mototaxista":
            return self.queryset.filter(mototaxista=user)
        elif user.rol == "pasajero":
            return self.queryset.filter(viaje__pasajero=user)
        return Oferta.objects.none()

    def create(self, request, *args, **kwargs):
        """Sobreescribir create para mejor manejo de errores"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        viaje_id = request.data.get('viaje')
        monto = request.data.get('monto')
        
        if user.rol != 'mototaxista':
            return Response(
                {"error": "Solo los mototaxistas pueden ofertar."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            viaje = Viaje.objects.get(pk=viaje_id)
        except Viaje.DoesNotExist:
            return Response(
                {"error": "El viaje no existe."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validar en una sola consulta
        tiene_actividad = Viaje.objects.filter(
            Q(mototaxista=user, estado__in=['aceptado', 'en_curso']) |
            Q(ofertas__mototaxista=user, ofertas__viaje__estado='pendiente')
        ).exists()
        
        if tiene_actividad:
            return Response(
                {"error": "Ya tienes una oferta activa o viaje en curso."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if viaje.estado != 'pendiente':
            return Response(
                {"error": "Este viaje ya no está disponible."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Guardar la oferta
        serializer.save(
            mototaxista=user,
            viaje=viaje,
            monto=monto,
            tiempo_estimado=request.data.get('tiempo_estimado', '15-30 min')
        )
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['patch'])
    def aceptar(self, request, pk=None):
        """El pasajero acepta una oferta - optimizado con transacción"""
        with transaction.atomic():
            oferta = self.get_object()
            viaje = oferta.viaje
            user = request.user
            
            if user != viaje.pasajero:
                return Response(
                    {'error': 'Solo el pasajero puede aceptar una oferta.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Verificar si ya hay oferta aceptada
            if Oferta.objects.filter(viaje=viaje, aceptada=True).exists():
                return Response(
                    {'error': 'Ya hay una oferta aceptada para este viaje.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # ✅ Aceptar la oferta
            oferta.aceptada = True
            oferta.save()
            
            # Actualizar viaje
            viaje.mototaxista = oferta.mototaxista
            viaje.costo_final = oferta.monto
            viaje.estado = 'aceptado'
            viaje.save()
            
            # ❌ Rechazar las demás ofertas
            Oferta.objects.filter(viaje=viaje).exclude(pk=oferta.pk).update(aceptada=False)
            
            # Actualizar disponibilidad del mototaxista
            try:
                mototaxi = Mototaxi.objects.get(conductor=oferta.mototaxista)
                mototaxi.disponible = False
                mototaxi.save()
            except Mototaxi.DoesNotExist:
                pass

            return Response({
                'mensaje': 'Oferta aceptada correctamente.',
                'viaje_id': viaje.id,
                'mototaxista': oferta.mototaxista.username,
                'estado_viaje': viaje.estado
            }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'])
    def cancelar_viaje(self, request, pk=None):
        with transaction.atomic():
            user = request.user
            oferta = Oferta.objects.filter(viaje=pk).delete()
            viaje = Viaje.objects.filter(viaje=pk).delete()
            return Response({
                'mensaje': 'Viaje eliminada correctamente.',
                'viaje_id': pk,
                'mototaxista': user.username,
            }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'])
    def rechazar(self, request, pk=None):
        with transaction.atomic():
            user = request.user
            oferta = Oferta.objects.filter(viaje=pk, mototaxista=user).delete()
            return Response({
                'mensaje': 'Oferta eliminada correctamente.',
                'oferta_id': pk,
                'mototaxista': user.username,
            }, status=status.HTTP_200_OK)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
            
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
        }
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer