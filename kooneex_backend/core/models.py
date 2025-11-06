from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class Usuario(AbstractUser):
    ROLES = (
        ('admin', 'Administrador'),
        ('mototaxista', 'Mototaxista'),
        ('pasajero', 'Pasajero'),
    )
    rol = models.CharField(max_length=20, choices=ROLES, default='pasajero')
    telefono = models.CharField(max_length=15, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)


    def __str__(self):
        return f"{self.username} ({self.rol})"

class Mototaxi(models.Model):
    conductor = models.OneToOneField('Usuario', on_delete=models.CASCADE, limit_choices_to={'rol': 'mototaxista'})
    placa = models.CharField(max_length=10)
    modelo = models.CharField(max_length=50)
    capacidad = models.PositiveIntegerField(default=4)
    disponible = models.BooleanField(default=True)
    
    # Campos nuevos de geolocalización
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.placa} - {self.conductor.username}"

class Viaje(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('negociando', 'negociando'),
        ('aceptado', 'Aceptado'),
        ('en_curso', 'En curso'),
        ('completado_pasajero', 'Completado'),
        ('completado', 'Completado'),
        ('rechazado', 'Rechazado'),
    ]

    tarifa_sugerida = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    tarifa_final = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    pasajero = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='viajes')
    mototaxista = models.ForeignKey('Usuario', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'rol': 'mototaxista'}, related_name='viajes_mototaxista')
    origen_lat = models.FloatField()
    origen_lon = models.FloatField()
    destino_lat = models.FloatField()
    destino_lon = models.FloatField()
    cantidad_pasajeros = models.PositiveIntegerField(default=1)
    distancia_km = models.FloatField(null=True, blank=True)
    costo_estimado = models.FloatField(null=True, blank=True)
    estado = models.CharField(max_length=20,choices=ESTADOS,default='pendiente')
    creado_en = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Viaje #{self.id} - {self.pasajero.username} ({self.estado})"


class Oferta(models.Model):
    viaje = models.ForeignKey(Viaje, related_name='ofertas', on_delete=models.CASCADE)
    mototaxista = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tiempo_estimado = models.CharField(max_length=50)
    aceptada = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Oferta {self.monto} por {self.mototaxista}"


class Pago(models.Model):
    viaje = models.OneToOneField(Viaje, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=8, decimal_places=2)
    metodo = models.CharField(max_length=50, choices=[('efectivo', 'Efectivo'), ('tarjeta', 'Tarjeta')], default='efectivo')
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago de {self.monto} por {self.viaje}"



