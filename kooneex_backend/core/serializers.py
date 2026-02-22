from rest_framework import serializers
from .models import (Usuario, 
                     Mototaxi, 
                     Viaje, 
                     Pago, 
                     Oferta,
                     Tarifa
                     )
from math import radians, sin, cos, sqrt, atan2
from decimal import Decimal

class UsuarioSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    class Meta:
        model = Usuario
        fields = ['id', 
                  'username', 
                  'first_name', 
                  'last_name',
                  'nombre_completo', 
                  'rol', 
                  'telefono',
                  'foto',
                  ]

class UsuarioRegistroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            "username",
            "password",
            "first_name",
            "last_name",
            "telefono",
            "rol",
            "foto",
        ]
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user

class MototaxiSerializer(serializers.ModelSerializer):
    conductor = UsuarioSerializer(read_only=True)

    class Meta:
        model = Mototaxi
        fields = [
            'id', 
            'conductor', 
            'placa', 
            'modelo', 
            'capacidad',
            'disponible', 
            'latitud', 
            'longitud'
        ]


class OfertaSerializer(serializers.ModelSerializer):
    # Campos optimizados - sin métodos duplicados
    mototaxista_nombre = serializers.CharField(
        source='mototaxista.nombre_completo',
        read_only=True
    )
    mototaxista_telefono = serializers.CharField(
        source='mototaxista.telefono',
        read_only=True,
        default="No disponible"  # Valor por defecto
    )

    mototaxista_foto = serializers.SerializerMethodField()
    
    class Meta:
        model = Oferta
        fields = [
            'id', 'viaje', 'monto', 'tiempo_estimado', 'aceptada', 'creada_en',
            'mototaxista', 'mototaxista_nombre', 'mototaxista_telefono', 'mototaxista_foto'
        ]
        read_only_fields = ['mototaxista', 'aceptada', 'creada_en']
    
    def get_mototaxista_foto(self, obj):
        request = self.context.get("request")

        if obj.mototaxista.foto:
            url = obj.mototaxista.foto.url
            return request.build_absolute_uri(url) if request else url

        return None
    
    def get_mototaxista_nombre(self, obj):
        # Acceso rápido a datos ya cargados con select_related
        return obj.nombre_completo
    
    def get_mototaxista_telefono(self, obj):
        # Para mostrar contacto cuando se acepta la oferta
        return obj.mototaxista.telefono or "No disponible"

    def create(self, validated_data):
        # Crear la instancia correctamente
        oferta = Oferta.objects.create(**validated_data)
        return oferta

class ViajeSerializer(serializers.ModelSerializer):

    pasajero_nombre = serializers.SerializerMethodField()
    mototaxista_nombre = serializers.SerializerMethodField()
    ofertas_count = serializers.SerializerMethodField()
    ofertas = OfertaSerializer(many=True, read_only=True)
    distancia_km = serializers.SerializerMethodField()
    pasajero_foto = serializers.SerializerMethodField()

    class Meta:
        model = Viaje
        fields = [
            'id', 'origen_lat', 'origen_lon', 'destino_lat', 'destino_lon',
            'cantidad_pasajeros', 'costo_estimado', 'costo_final', 'estado', 
            'pasajero_nombre', 'mototaxista_nombre', 'ofertas_count', 'ofertas', 
            'distancia_km', 'referencia', 'pasajero_foto'
        ]
        read_only_fields = ['pasajero']
    
    def get_pasajero_foto(self, obj):
        request = self.context.get("request")
        if obj.pasajero and obj.pasajero.foto:
            return request.build_absolute_uri(obj.pasajero.foto.url)
        return None
    
    def create(self, validated_data):
        user = self.context['request'].user
        cantidad = validated_data.get('cantidad_pasajeros', 1)
        origen_lat = validated_data['origen_lat']
        origen_lon = validated_data['origen_lon']
        destino_lat = validated_data['destino_lat']
        destino_lon = validated_data['destino_lon']
        distancia_km = self._haversine(origen_lat, origen_lon, destino_lat, destino_lon)


        # Obtener tarifa activa
        tarifa = Tarifa.objects.filter(activa=True).first()
        if not tarifa:
            raise serializers.ValidationError(
                "No hay tarifa activa configurada."
            )

        # Cálculo del costo
        costo_estimado = (tarifa.tarifa * cantidad) + tarifa.comision
        
        return Viaje.objects.create(
            pasajero=user,
            distancia_km=distancia_km,
            costo_estimado=costo_estimado,
            **validated_data
        )
    
    def get_distancia_km(self, obj):
        if not obj.origen_lat or not obj.origen_lon or not obj.destino_lat or not obj.destino_lon:
            return None
        return self._haversine(obj.origen_lat, obj.origen_lon, obj.destino_lat, obj.destino_lon)

    # Fórmula de Haversine
    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371  # Radio de la Tierra en km

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return round(R * c, 2)  # Redondeado a 2 decimales
    
    def get_pasajero_nombre(self, obj):
        return obj.pasajero.username
    
    def get_mototaxista_nombre(self, obj):
        return obj.mototaxista.username if obj.mototaxista else None
    
    def get_ofertas_count(self, obj):
        """Contar ofertas de manera eficiente"""
        # Si ya se hizo prefetch, podemos usar all()
        if hasattr(obj, '_prefetched_objects_cache') and 'ofertas' in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache['ofertas'])
        
        # Si no, usar count() que es optimizado por Django
        return obj.ofertas.count()

    def validate(self, data):
        user = self.context['request'].user
        if user.rol == 'pasajero':
            # Validación más eficiente
            tiene_viaje_activo = Viaje.objects.filter(
                pasajero=user,
                estado__in=['pendiente', 'aceptado', 'en_curso']
            ).exists()
        
            if tiene_viaje_activo:
                raise serializers.ValidationError(
                    "Ya tienes un viaje activo. Completa o cancela antes de solicitar otro."
                )
        return data


class PagoSerializer(serializers.ModelSerializer):
    viaje = ViajeSerializer(read_only=True)

    class Meta:
        model = Pago
        fields = ['id', 
                  'viaje', 
                  'monto', 
                  'metodo', 
                  'fecha']

