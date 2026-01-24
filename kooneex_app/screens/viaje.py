import requests
from kivymd.uix.screen import MDScreen
from kivymd.uix.menu import MDDropdownMenu
from kivy.properties import StringProperty, BooleanProperty
from helpers import get_headers
from config import DEFAULT_LAT, DEFAULT_LON, DESTINOS_PREDEFINIDOS, API_URL
from kivy.metrics import dp
from kivy.utils import platform
if platform == 'android':
    from plyer import gps
else:
    gps = None

class ViajeScreen(MDScreen):
    origen_seleccionado = BooleanProperty(False)
    mensaje = StringProperty("")
    origen_lat = None
    origen_lon = None
    destino_lat = None
    destino_lon = None
    referencia = None
    menu_destinos = None

    def on_enter(self, *args):
        #Al iniciar la pantalla obtenemos la ubicacion mediante gps
        self.obtener_ubicacion()

    def obtener_ubicacion(self):
        try:
            # Solo Android tiene GPS funcional
            if platform != "android":
                raise Exception("GPS no disponible fuera de Android")
                
            gps.configure(on_location=self.on_location, on_status=self.on_status)
            gps.start(minTime=1000, minDistance=0)
        except Exception as e:
            print("GPS no disponible:", e)
            self._usar_ubicacion_como_origen(lat=DEFAULT_LAT, lon=DEFAULT_LON)

    def _usar_ubicacion_como_origen(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")

        if not lat or not lon:
            print("GPS inválido, usando ubicación por defecto.")
            lat, lon = DEFAULT_LAT, DEFAULT_LON

        print("Origen definido automáticamente en:", lat, lon)

        # guardar coordenadas del origen
        self.origen_lat = lat
        self.origen_lon = lon

        # ya no necesitamos seguir escuchando GPS (evita gastar batería)
        try:
            gps.stop()
        except:
            pass

    def on_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")

        if not lat or not lon:
            self.set_default_location()
            return

        print("Ubicación detectada:", lat, lon)
        self.manejar_ubicacion(lat, lon)
        gps.stop()

    def on_status(self, stype, status):
        print("GPS status:", stype, status)

    def set_default_location(self):
        print("Usando ubicación por defecto")
        self.manejar_ubicacion(DEFAULT_LAT, DEFAULT_LON)

    
    def abrir_lista_destinos(self):
        # Cerrar menú previo si existía
        if self.menu_destinos:
            self.menu_destinos.dismiss()

        # Construir items del menú
        items = []
        for nombre, (lat, lon) in DESTINOS_PREDEFINIDOS.items():
            items.append({
                "viewclass": "OneLineListItem",
                "text": nombre,
                "height": dp(48),
                "on_release": lambda nombre=nombre, lat=lat, lon=lon:
                    self.seleccionar_destino_predefinido(nombre, lat, lon)
            })

        # Crear menú
        self.menu_destinos = MDDropdownMenu(
            caller=self.ids.txt_destino,
            items=items,
            width_mult=4,
            max_height=dp(200),
            position = "center"
        )
        self.menu_destinos.open()
    
    def seleccionar_destino_predefinido(self, nombre, lat, lon):
        if self.menu_destinos:
            self.menu_destinos.dismiss()

        # Rellenar el campo
        self.ids.txt_destino.text = nombre

        # Guardar coordenadas
        self.destino_lat = lat
        self.destino_lon = lon

        print("Destino marcado:", nombre, lat, lon)

    def solicitar_viaje(self):
        try:
            if not all([self.origen_lat, self.origen_lon]):
                self.mensaje = "Selecciona un origen válido."
                return

            if not all([self.destino_lat, self.destino_lon]):
                self.mensaje = "Selecciona un destino válido."
                return

            cantidad = self.ids.txt_cantidad_pasajeros.text
            if not cantidad.isdigit() or int(cantidad) < 1:
                self.mensaje = "Cantidad de pasajeros inválida."
                return

            self.referencia = self.ids.txt_referencia.text
            
            datos = {
                "origen_lat": self.origen_lat,
                "origen_lon": self.origen_lon,
                "destino_lat": self.destino_lat,
                "destino_lon": self.destino_lon,
                "cantidad_pasajeros": int(cantidad),
                "referencia": self.referencia,
            }

            headers = get_headers()
            resp = requests.post(f"{API_URL}/viajes/", json=datos, headers=headers)

            if resp.status_code == 201:
                self.manager.current = "tarifas"
            else:
                self.mensaje = f"Error: {resp.text}"

        except Exception as e:
            self.mensaje = f"Error de conexión: {e}"
