import requests
from kivy_garden.mapview import MapMarker, MapSource
from kivy.graphics import Color, Line
from kivymd.uix.screen import MDScreen
from kivy.clock import Clock, mainthread
from config import DEFAULT_LAT, DEFAULT_LON, API_URL
from kivy.utils import platform
if platform == 'android':
    from plyer import gps
else:
    gps = None

class ViajeEnCursoMotoScreen(MDScreen):
    origen_lat = None
    origen_lon = None
    destino_lat = None
    destino_lon = None
    origen_marker = None
    destino_marker = None
    ruta_linea = None

    def on_enter(self, *args):
        self.obtener_ubicacion()
        self.cargar_destino_desde_api()
        Clock.schedule_interval(lambda dt: self.dibujar_ruta(), 0.3)
        self.iniciar_seguimiento_gps()

    def obtener_ubicacion(self):
        if platform != "android":
            print("GPS no disponible fuera de Android")
            self._usar_ubicacion_como_origen(
                lat=DEFAULT_LAT,
                lon=DEFAULT_LON
            )
            return
        if gps is None:
            print("GPS no inicializado")
            return
        try:
            gps.configure(on_location=self.on_location, on_status=self.on_status)
            gps.start(minTime=1000, minDistance=0)
        except Exception as e:
            print("Error iniciando GPS:", e)
            self._usar_ubicacion_como_origen(lat=DEFAULT_LAT, lon=DEFAULT_LON)
    

    def _usar_ubicacion_como_origen(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")

        if not lat or not lon:
            print("GPS inválido, usando ubicación por defecto.")
            lat, lon = DEFAULT_LAT, DEFAULT_LON

        print("Origen definido automáticamente en:", lat, lon)

        # coloca el origen en el mapa
        self._actualizar_mapa("origen", lat, lon)

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
    
    def marcar_destino(self, lat, lon):
        self.destino_lat = lat
        self.destino_lon = lon
        self._actualizar_mapa("destino", lat, lon)
    
    def cargar_destino_desde_api(self):
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()

            with open("viaje_actual.txt", "r") as f:
                viaje_id = f.read().strip()

            headers = {
                "Authorization": f"Bearer {token}"
            }

            resp = requests.get(
                f"{API_URL}/viajes/{viaje_id}/",
                headers=headers,
                timeout=10
            )

            if resp.status_code != 200:
                print("Error obteniendo viaje:", resp.text)
                return

            data = resp.json()

            lat = data.get("destino_lat")
            lon = data.get("destino_lon")

            if not lat or not lon:
                print("Destino no definido en el viaje")
                return

            print("Destino cargado desde API:", lat, lon)
            self.marcar_destino(lat, lon)

        except Exception as e:
            print("Error cargando destino:", e)
    

    def dibujar_ruta(self):
        if not self.origen_lat or not self.destino_lat:
            return

        mapa = self.ids.mapa
        zoom = mapa.zoom

        # convertir lat/lon a coordenadas de pantalla
        x1, y1 = mapa.get_window_xy_from(self.origen_lat, self.origen_lon, zoom)
        x2, y2 = mapa.get_window_xy_from(self.destino_lat, self.destino_lon, zoom)

        # eliminar línea anterior
        if self.ruta_linea:
            mapa.canvas.after.remove(self.ruta_linea)
            self.ruta_linea = None

        with mapa.canvas.after:
            Color(0, 0.5, 1, 0.85)  # azul tipo Uber
            self.ruta_linea = Line(
                points=[x1, y1, x2, y2],
                width=4
            )

    
    
    @mainthread
    def actualizar_posicion(self, lat, lon):
        mapa = self.ids.mapa

        if not self.origen_marker:
            self.origen_marker = MapMarker(lat=lat, lon=lon)
            mapa.add_widget(self.origen_marker)
        else:
            self.origen_marker.lat = lat
            self.origen_marker.lon = lon

        mapa.center_on(lat, lon)

    
    @mainthread
    def _actualizar_mapa(self, tipo, lat, lon):
        mapa = self.ids.mapa
        mapa.center_on(lat, lon)

        if tipo == "origen":
            if self.origen_marker:
                mapa.remove_widget(self.origen_marker)

            self.origen_marker = MapMarker(lat=lat, lon=lon, source="assets/row.png")
            mapa.add_widget(self.origen_marker)

            self.origen_lat = lat
            self.origen_lon = lon

        elif tipo == "destino":
            if self.destino_marker:
                mapa.remove_widget(self.destino_marker)

            self.destino_marker = MapMarker(lat=lat, lon=lon)
            mapa.add_widget(self.destino_marker)

            self.destino_lat = lat
            self.destino_lon = lon
    
    def iniciar_seguimiento_gps(self):
        if platform != "android" or gps is None:
            print("Seguimiento GPS no disponible")
            return

        try:
            gps.configure(
                on_location=self.on_location_en_curso,
                on_status=self.on_status
            )
            gps.start(minTime=2000, minDistance=1)
            print("📡 Seguimiento GPS activo")
        except Exception as e:
            print("Error iniciando seguimiento GPS:", e)

    def on_location_en_curso(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        speed = kwargs.get("speed", 0)  # m/s

        if not lat or not lon:
            return
        

        # Ignorar ruido GPS (menos de 0.5 m/s ≈ 1.8 km/h)
        if speed is not None and speed < 0.5:
            return

        self.actualizar_origen(lat, lon)
    
    @mainthread
    def actualizar_origen(self, lat, lon):
        mapa = self.ids.mapa

        # actualizar datos
        self.origen_lat = lat
        self.origen_lon = lon

        # crear o mover marker
        if not self.origen_marker:
            self.origen_marker = MapMarker(lat=lat, lon=lon, source="assets/row.png")
            mapa.add_widget(self.origen_marker)
            mapa.center_on(lat, lon)  # solo la primera vez
        else:
            self.origen_marker.lat = lat
            self.origen_marker.lon = lon

        # actualizar ruta
        if self.destino_lat:
            self.dibujar_ruta()


    def marcar_completado(self):
        """Permite al mototaxista marcar su viaje como completado"""
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()
            with open("viaje_actual.txt", "r") as f:
                viaje_id = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}
            datos = {"estado": "completado"}

            resp = requests.patch(f"{API_URL}/viajes/{viaje_id}/", json=datos, headers=headers)

            if resp.status_code in [200, 202]:
                self.manager.get_screen('pendientes').cargar_viajes_pendientes()
                self.manager.current = "pendientes"
                return
            else:
                self.ids.info_label.text = f"❌ Error al completar: {resp.text}"

        except Exception as e:
            print(f'Error: {e}')
    