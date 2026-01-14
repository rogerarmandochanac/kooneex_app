from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    ROLES = (
        ('admin', 'Administrador'),
        ('mototaxista', 'Mototaxista'),
        ('pasajero', 'Pasajero'),
    )
    rol = models.CharField(max_length=20, choices=ROLES, default='pasajero')
    telefono = models.CharField(max_length=15, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['rol']),
        ]

    def __str__(self):
        return f"{self.username} ({self.rol})"

    @property
    def nombre_completo(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username


class Mototaxi(models.Model):
    conductor = models.OneToOneField('Usuario', on_delete=models.CASCADE, 
                                    limit_choices_to={'rol': 'mototaxista'})
    placa = models.CharField(max_length=10)
    modelo = models.CharField(max_length=50)
    capacidad = models.PositiveIntegerField(default=4)
    disponible = models.BooleanField(default=True)
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['disponible']),
            models.Index(fields=['conductor']),
            models.Index(fields=['latitud', 'longitud']),
        ]

    def __str__(self):
        return f"{self.placa} - {self.conductor.username}"
    
    def actualizar_ubicacion(self, lat, lon):
        """Método para actualizar ubicación"""
        self.latitud = lat
        self.longitud = lon
        self.save(update_fields=['latitud', 'longitud'])


class Viaje(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('aceptado', 'Aceptado'),
        ('en_curso', 'En curso'),
        ('completado', 'Completado'),
        ('rechazado', 'Rechazado'),
    ]
    
    pasajero = models.ForeignKey('Usuario', on_delete=models.CASCADE, 
                                related_name='viajes')
    mototaxista = models.ForeignKey('Usuario', on_delete=models.SET_NULL, 
                                   null=True, blank=True, 
                                   limit_choices_to={'rol': 'mototaxista'}, 
                                   related_name='viajes_mototaxista')
    origen_lat = models.FloatField()
    origen_lon = models.FloatField()
    destino_lat = models.FloatField()
    destino_lon = models.FloatField()
    cantidad_pasajeros = models.PositiveIntegerField(default=1)
    referencia = models.CharField(max_length=100, blank=False) #Para colocar un texto con la ubicacion de referencia
    distancia_km = models.FloatField(null=True, blank=True)
    costo_estimado = models.DecimalField(max_digits=10, decimal_places=2, 
                                        null=True, blank=True)
    costo_final = models.DecimalField(max_digits=10, decimal_places=2, 
                                     null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['pasajero', 'estado']),
            models.Index(fields=['mototaxista', 'estado']),
            models.Index(fields=['estado', 'creado_en']),
            models.Index(fields=['origen_lat', 'origen_lon']),
        ]

    def __str__(self):
        return f"Viaje #{self.id} - {self.pasajero.username} ({self.estado})"
    
    def calcular_distancia(self):
        """Calcula distancia entre origen y destino"""
        from math import radians, sin, cos, sqrt, atan2
        
        lat1, lon1 = radians(self.origen_lat), radians(self.origen_lon)
        lat2, lon2 = radians(self.destino_lat), radians(self.destino_lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        R = 6371.0  # Radio de la Tierra en km
        distancia = R * c
        
        # Guardar si no está calculada
        if not self.distancia_km:
            self.distancia_km = round(distancia, 2)
            self.save(update_fields=['distancia_km'])
        
        return distancia


class Oferta(models.Model):
    viaje = models.ForeignKey(Viaje, related_name='ofertas', on_delete=models.CASCADE)
    mototaxista = models.ForeignKey('Usuario', on_delete=models.CASCADE, 
                                   limit_choices_to={'rol':'mototaxista'})
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tiempo_estimado = models.CharField(max_length=50)
    aceptada = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['mototaxista', 'aceptada']),
            models.Index(fields=['viaje', 'aceptada']),
            models.Index(fields=['creada_en']),
        ]
        ordering = ['-creada_en']

    def __str__(self):
        return f"Oferta ${self.monto} por {self.mototaxista.username}"


class Pago(models.Model):
    viaje = models.OneToOneField(Viaje, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=8, decimal_places=2)
    metodo = models.CharField(max_length=50, 
                             choices=[('efectivo', 'Efectivo'), ('tarjeta', 'Tarjeta')], 
                             default='efectivo')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['viaje']),
        ]

    def __str__(self):
        return f"Pago de ${self.monto} por {self.viaje}"