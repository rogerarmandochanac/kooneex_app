from rest_framework import serializers
from .models import Usuario, Mototaxi, Viaje, Pago

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'username', 'first_name', 'last_name', 'rol', 'telefono', 'direccion']


class MototaxiSerializer(serializers.ModelSerializer):
    conductor = UsuarioSerializer(read_only=True)

    class Meta:
        model = Mototaxi
        fields = [
            'id', 'conductor', 'placa', 'modelo', 'capacidad',
            'disponible', 'latitud', 'longitud'
        ]


class ViajeSerializer(serializers.ModelSerializer):
    pasajero = UsuarioSerializer(read_only=True)
    mototaxi = MototaxiSerializer(read_only=True)

    class Meta:
        model = Viaje
        fields = '__all__'
        read_only_fields = ['pasajero']
    
    def validate(self, data):
        user = self.context['request'].user
        if user.rol == 'pasajero':
            activo = Viaje.objects.filter(pasajero=user, estado__in=['pendiente', 'aceptado']).exists()
            if activo:
                raise serializers.ValidationError("Ya tienes un viaje activo o pendiente.")
        return data



class PagoSerializer(serializers.ModelSerializer):
    viaje = ViajeSerializer(read_only=True)

    class Meta:
        model = Pago
        fields = ['id', 'viaje', 'monto', 'metodo', 'fecha']
