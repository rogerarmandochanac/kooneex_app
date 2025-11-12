from rest_framework import serializers
from .models import (Usuario, 
                     Mototaxi, 
                     Viaje, 
                     Pago, 
                     Oferta
                     )

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 
                  'username', 
                  'first_name', 
                  'last_name', 
                  'rol', 
                  'telefono', 
                  'direccion'
                  ]


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
    mototaxista_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Oferta
        fields = '__all__'
        read_only_fields = ['mototaxista']

    def get_mototaxista_nombre(self, obj):
        # Evita fallar si obj es un dict o no tiene 'mototaxista'
        mototaxista = getattr(obj, 'mototaxista', None)
        if mototaxista:
            nombre = f"{mototaxista.first_name} {mototaxista.last_name}".strip()
            return nombre or mototaxista.username
        return None

    def create(self, validated_data):
        # Crear la instancia correctamente
        oferta = Oferta.objects.create(**validated_data)
        return oferta

class ViajeSerializer(serializers.ModelSerializer):
    ofertas = OfertaSerializer(many=True, read_only=True)
    pasajero = UsuarioSerializer(read_only=True)
    mototaxista = UsuarioSerializer(read_only=True)

    class Meta:
        model = Viaje
        fields = '__all__'
        read_only_fields = ['pasajero']
        depth = 1

    def validate(self, data):
        user = self.context['request'].user
        if user.rol == 'pasajero':
            activo = Viaje.objects.filter(
                pasajero=user,
                estado__in=['pendiente', 'aceptado']
            ).exists()
            if activo:
                raise serializers.ValidationError("Ya tienes un viaje activo o pendiente.")
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

