import requests
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty, NumericProperty
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.core.text import LabelBase
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from helpers import get_headers, save_headers
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.image import Image
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDRectangleFlatButton
from kivy_garden.mapview import MapView, MapMarkerPopup
from kivy.clock import Clock, mainthread
from kivy_garden.mapview import MapMarker, MapSource
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import OneLineListItem
from kivy.metrics import dp
from kivy.utils import platform
if platform == 'android':
    from plyer import gps
else:
    gps = None
from kivy.graphics import Color, Line

Window.size = (360, 640)

API_URL = "http://127.0.0.1:8000/api"

DEFAULT_LAT = 20.1373
DEFAULT_LON = -90.1749

DESTINOS_PREDEFINIDOS = {
    "Pomuch Centro": (20.13730, -90.17490),
    "Pomuch Soledad": (20.145780, -90.173459),
    "Pomuch Nueva": (20.144052896584597, -90.17682172260673),
    "Pomuch San Francisco": (20.146953764112478, -90.16952611440409),
    "Pomuch Villa Lucrecia": (20.14155488415286, -90.16592122564514),
    "Pomuch San Diego": (20.141151975180843, -90.17287351110882),
    "Pomuch Santa Cristina": (20.135914063988263, -90.16540624153673),
    "Pomuch San pedro I": (20.13285181919244, -90.17321683384776),
    "Pomuch San pedro II": (20.12680773892196, -90.17690755329146),
    "Pomuch Benito Juarez": (20.12962833879734, -90.1786241669862),
    "Pomuch Hacienda Dzodzil": (20.16802372650526, -90.23085213931239),
}

class FlechaMarker(MapMarker):
    angle = NumericProperty(0)

class LoginScreen(MDScreen):
    username = StringProperty("")
    password = StringProperty("")
    mensaje = StringProperty("")
    show_password = BooleanProperty(False)

    def toggle_password(self):
        print(self.show_password)
        self.show_password = not self.show_password
        

    def login(self):
        datos = {"username": self.username, "password": self.password}
        try:
            resp = requests.post(f"{API_URL}/token/", json=datos, timeout=10)
            
            if resp.ok:               
                access_token = resp.json().get("access")
                headers = save_headers(access_token)
                user_resp = requests.get(f"{API_URL}/usuario/", headers=headers, timeout=10)

                if resp.ok:
                    rol = user_resp.json().get("rol")

                    if rol == "pasajero":
                        self.evaluar_viaje_pasajero()
                    
                    elif rol == "mototaxista":
                        self.evaluar_viaje_mototaxista()
                    
                    else:
                        self.mensaje = "Rol desconocido."
                
                else:
                    self.mensaje = "Error al obtener usuario."
            
            else:
                self.mensaje = "Credenciales incorrectas"
        
        except Exception as e:
            self.mensaje = f"Error de conexión: {e}"

    def evaluar_viaje_pasajero(self):
        try:
            resp = requests.get(f"{API_URL}/viajes/verificar_viajes_activos/", headers=get_headers(), timeout=10)
            data = resp.json()
            if resp.ok:
                if data.get("mensaje") == "tiene_viaje_activo":
                    viaje_en_curso = self.manager.get_screen("viaje_en_curso")
                    viaje_en_curso.cargar_viaje_en_curso()
                    self.manager.current = "viaje_en_curso"
                
                elif data.get("mensaje") == 'tiene_viaje_pendiente':
                    self.manager.current = 'tarifas'
                    return
                
                elif estado == None:
                    self.manager.current = "viaje"
            else:
                print("Error al verificar viajes:", resp.text)
                self.manager.current = "viaje"

        except Exception as e:
            print("Error al verificar viaje activo:", e)
            self.manager.current = "viaje"
    
    def evaluar_viaje_mototaxista(self):
        try:
            resp = requests.get(f"{API_URL}/viajes/verificar_viajes_activos/", headers=get_headers(), timeout=10)
            data = resp.json()
            if resp.ok:
                if data.get("mensaje") == "tiene_viaje_aceptado":
                    self.manager.get_screen("viaje_aceptado_moto").cargar_viaje_en_curso()
                    self.manager.current = "viaje_aceptado_moto"
                    return
                elif data.get("mensaje") == 'tiene_viaje_en_curso':
                    self.manager.get_screen('viaje_en_curso_moto')
                    self.manager.current = 'viaje_en_curso_moto'
                    return
                elif data.get("mensaje") == "tiene_viaje_ofertado":
                    self.manager.get_screen("pendientes").mostrar_espera_respuesta(data.get('viaje_id', None))
                    self.manager.current = "pendientes"
                    return

                elif data.get("mensaje") == 'None': 
                    self.manager.get_screen('pendientes').cargar_viajes_pendientes() 
                    self.manager.current = "pendientes"
                    return
                else:
                    print("Error al obtener viajes:", resp_viajes.text)
                    self.manager.get_screen('pendientes').cargar_viajes_pendientes() 
                    self.manager.current = "pendientes"
            
            else:
                print("Error al obtener viajes:", resp_viajes.text)
                
        except Exception as e:
            print("Error al verificar estado del mototaxista:", e)

class ViajeScreen(Screen):
    origen_seleccionado = BooleanProperty(False)
    mensaje = StringProperty("")
    buscar_evento = None
    origen_lat = None
    origen_lon = None
    destino_lat = None
    destino_lon = None
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

            datos = {
                "origen_lat": self.origen_lat,
                "origen_lon": self.origen_lon,
                "destino_lat": self.destino_lat,
                "destino_lon": self.destino_lon,
                "cantidad_pasajeros": int(cantidad),
            }

            headers = get_headers()
            resp = requests.post(f"{API_URL}/viajes/", json=datos, headers=headers)

            if resp.status_code == 201:
                self.manager.current = "tarifas"
            else:
                self.mensaje = f"Error: {resp.text}"

        except Exception as e:
            self.mensaje = f"Error de conexión: {e}"

# ==============================
# PANTALLA PRINCIPAL MOTOTAXISTA
# ==============================
class PendientesScreen(Screen):
    def cargar_viajes_pendientes(self):
        try:
            headers = get_headers()
            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            layout = self.ids.viajes_container
            layout.clear_widgets()

            if resp.status_code != 200:
                layout.add_widget(MDLabel(text="Error al cargar viajes.", theme_text_color="Error"))
                return

            viajes = resp.json()
            if not viajes:
                layout.padding = [24, 24, 24, 24]
                layout.add_widget(MDLabel(text="No hay viajes pendientes.", halign="center"))
                return

            for v in viajes:
                card = MDCard(
                    orientation="vertical",
                    padding=15,
                    spacing=10,
                    size_hint_y=None,
                    height=250,
                    radius=14,
                    md_bg_color=(0.98, 0.97, 0.95, 1),
                    elevation=0,
                    shadow_softness = 0,
                    shadow_color = (0,0,0,0),
                )
                
                content_container = MDBoxLayout(
                    orientation = 'horizontal',
                    spacing = 5,
                )

                content = MDBoxLayout(
                    orientation = "vertical",
                    spacing = 5,

                )

                content.add_widget(MDLabel(
                    text=f"Usuario: [b]{v['pasajero_nombre']}[/b]",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content.add_widget(MDLabel(
                    text=f"Pasajeros: [b]{v.get('cantidad_pasajeros', 1)}[/b]",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content.add_widget(MDLabel(
                    text=f"Tarifa sugerida: [b]${v.get('costo_estimado', 0)}[b]",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content.add_widget(MDLabel(
                    text=f"Distancia: [b]{v.get('distancia_km', 0)}[b] km",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content_container.add_widget(content)
                content_container.add_widget( Image(
                        source="assets/user_placeholder.png",
                        allow_stretch=True,   # se adapta al contenedor
                        keep_ratio=True,
                        size_hint = (None, None),
                        size = (80, 80),
                    ))
                card.add_widget(content_container)

                # -------- CAMPO TARIFA ---------
                tarifa_input = MDTextField(
                    hint_text="Tu tarifa (opcional)",
                    text=str(v.get("costo_estimado", "")),
                    mode="rectangle",
                    size_hint_y=None,
                    height=60
                )
                card.add_widget(tarifa_input)

                # -------- BOTONES ----------
                btn_box = BoxLayout(size_hint_y=None, height=55, spacing=10)

                btn_box.add_widget(MDRaisedButton(
                    text="Sugerir tarifa",
                    md_bg_color=(0.2, 0.2, 0.2, 1),
                    on_release=lambda x, vid=v["id"], tinput=tarifa_input:
                        self.sugerir_tarifa(vid, tinput.text)
                ))

                card.add_widget(btn_box)

                layout.add_widget(card)

        except Exception as e:
            layout.clear_widgets()
            layout.add_widget(MDLabel(text=f"Error: {e}", theme_text_color="Error"))

    
    def sugerir_tarifa(self, viaje_id, tarifa):
        """El mototaxista sugiere una tarifa personalizada y bloquea otras opciones."""
        try:
            headers = get_headers()
            datos = {}

            if tarifa:
                try:
                    datos["monto"] = float(tarifa)
                except ValueError:
                    print("Tarifa no válida")
            datos['viaje'] = viaje_id
            datos['tiempo_estimado'] = 30

            resp = requests.post(f"{API_URL}/ofertas/", json=datos, headers=headers)

            if resp.status_code in [200, 201]:
                print("✅ Tarifa sugerida correctamente.")
                
                # Bloquear botones y mostrar mensaje
                self.mostrar_espera_respuesta(viaje_id)

            else:
                print("Error al sugerir tarifa:", resp.text)

        except Exception as e:
            print("Error de conexión:", e)

    def rechazar_oferta(self, viaje_id):
        """El mototaxista rechaza la oferta de viaje."""
        try:
            headers = get_headers()
            datos = {"desicion": "rechazar"}
            resp = requests.delete(f"{API_URL}/ofertas/{viaje_id}/rechazar/", json=datos, headers=headers)

            if resp.status_code in [200, 202]:
                self.cargar_viajes_pendientes()
            else:
                print("Error al rechazar viaje:", resp.text)
        except Exception as e:
            print("Error de conexión:", e)
    
    def mostrar_espera_respuesta(self, viaje_id):
        layout = self.ids.viajes_container
        layout.clear_widgets()

        # --- Card principal ---
        card = MDCard(
            orientation="vertical",
            size_hint_y=None,
            height=260,
            padding=20,
            spacing=15,
            radius=[0],
            elevation=0,
            md_bg_color=(1, 1, 1, 1),   # Blanco elegante
        )

        # --- Encabezado con icono ---
        header = MDBoxLayout(
            orientation="horizontal",
            spacing=15,
            size_hint_y=None,
            height=40
        )

        header.add_widget(MDIconButton(
        icon="clock-outline",
        theme_text_color="Custom",
        text_color=(0.15, 0.15, 0.15, 1),
        disabled=True,                # Para que no parezca botón clickeable
        icon_size="36sp"
        ))

        header.add_widget(MDLabel(
            text=f"Oferta pendiente",
            font_style="H6",
            bold=True,
            theme_text_color="Primary"
        ))

        card.add_widget(header)

        # Separador elegante
        card.add_widget(MDBoxLayout(
        size_hint_y=None,
        height=1,
        md_bg_color=(0.85, 0.85, 0.85, 1)
    ))

        # --- Mensajes principales ---
        card.add_widget(MDLabel(
            text=f"Has enviado una oferta para el viaje",
            font_style="Body1",
            theme_text_color="Primary"
        ))

        card.add_widget(MDLabel(
            text="Esperando respuesta del pasajero...",
            font_style="Body2",
            theme_text_color="Secondary"
        ))

        # --- Espacio antes del botón ---
        card.add_widget(MDLabel(text="", size_hint_y=None, height=10))

        # --- Botón centrado ---
        btn = MDRaisedButton(
            text="Cancelar oferta",
            md_bg_color=(0.85, 0.25, 0.15, 1),  # Rojo quemado que combina
            text_color=(1, 1, 1, 1),
            elevation=0,
            pos_hint={"center_x": 0.5},
            on_release=lambda x: self.rechazar_oferta(viaje_id)
        )

        card.add_widget(btn)
        layout.add_widget(card)


    def iniciar_viaje(self, viaje_id):
        """Inicia el viaje y pasa al screen de viaje en curso."""
        try:
            headers = get_headers()
            resp = requests.post(f"{API_URL}/viajes/{viaje_id}/iniciar/", headers=headers)

            if resp.status_code == 200:
                viaje = resp.json()
                viaje_screen = self.manager.get_screen("viaje_aceptado_moto")
                viaje_screen.mostrar_viaje(viaje)
                self.manager.current = "viaje_aceptado_moto"
            else:
                print(f"Error al iniciar viaje: {resp.text}")

        except Exception as e:
            print(f"Error de conexión: {e}")

# ==============================
# APLICACION VIAJE EN CURSO PARA EL MOTOTAXISTA
# ==============================
class ViajeEnCursoScreen(Screen):
    def cargar_viaje_en_curso(self):
        """Carga la información del viaje en curso del pasajero"""
        try:
            headers = get_headers()

            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            if resp.ok:
                viaje = resp.json()
                if viaje:
                    viaje = viaje[0]
                    if viaje['estado'] == 'en_curso':
                        self.ids.info_label.text = f"Su mototaxi con el mototaxista[b]{viaje.get('mototaxista_nombre')}[/b] esta en camino favor de estar pendiente."
                    else:
                        self.ids.info_label.text = (
                            f"Viaje {viaje['estado']} por el mototaxista {viaje.get('mototaxista_nombre')} con un costo final de ${viaje.get('costo_final')}"
                        )
            else:
                self.ids.info_label.text = "Error al cargar el viaje."

        except FileNotFoundError:
            self.ids.info_label.text = "No hay viaje activo."
        except Exception as e:
            self.ids.info_label.text = f"Error: {e}"


class ViajeAceptadoMotoScreen(Screen):
    def on_pre_enter(self):
        """Carga el viaje en curso del mototaxista al entrar en el screen"""
        self.cargar_viaje_en_curso()

    def cargar_viaje_en_curso(self):
        """Carga la información del viaje actual del mototaxista"""
        try:
            headers = get_headers()

            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            if resp.ok:
                viajes = resp.json()
                aceptado = next((v for v in viajes if v["estado"] in ["aceptado", "en_curso"]), None)

                if aceptado:
                    self.ids.info_label.text = (
                        f"Viaje #{aceptado['id']}\n"
                        f"Pasajero: {aceptado.get('pasajero_nombre')}\n"
                        f"Destino: {aceptado.get('destino_lat', 'N/A')}, {aceptado.get('destino_lon', 'N/A')}\n"
                        f"Distancia: {aceptado.get('distancia_km', 'N/A')} km.\n"
                        f"Tarifa: ${aceptado.get('costo_final', 'N/A')}\n"
                        f"Estado: {aceptado['estado']}"
                    )
                    # Guardar el ID del viaje actual en un archivo para referencia rápida
                    with open("viaje_actual.txt", "w") as f:
                        f.write(str(aceptado["id"]))
                else:
                    self.ids.info_label.text = "No tienes viajes en curso."
            else:
                self.ids.info_label.text = f"Error al cargar: {resp.text}"

        except Exception as e:
            self.ids.info_label.text = f"Error de conexión: {e}"

    def iniciar_viaje(self):
        """Permite al mototaxista marcar el viaje como 'en curso'"""
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()
            with open("viaje_actual.txt", "r") as f:
                viaje_id = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}
            datos = {"estado": "en_curso"}

            resp = requests.patch(f"{API_URL}/viajes/{viaje_id}/", json=datos, headers=headers)

            if resp.status_code in [200, 202]:
                viaje_screen = self.manager.get_screen("viaje_en_curso_moto")
                self.manager.current = "viaje_en_curso_moto"
                
            else:
                self.ids.info_label.text = f"❌ Error al iniciar: {resp.text}"

        except Exception as e:
            self.ids.info_label.text = f"Error: {e}"

class ViajeEnCursoMotoScreen(Screen):
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

            self.origen_marker = MapMarker(lat=lat, lon=lon)
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
            self.iniciar_gps_simulado()
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
            self.origen_marker = MapMarker(lat=lat, lon=lon)
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
                self.ids.info_label.text = "✅ Viaje completado correctamente."
            else:
                self.ids.info_label.text = f"❌ Error al completar: {resp.text}"

        except Exception as e:
            print(f'Error: {e}')
            #self.ids.info_label.text = f"Error: {e}"
    
    def iniciar_gps_simulado(self):
        # Ruta simulada (lat, lon)
        self.ruta_fake = [
            (20.137300, -90.174900),
            (20.137310, -90.174880),
            (20.137330, -90.174860),
            (20.137360, -90.174830),
            (20.137400, -90.174800),
        ]

        self._fake_index = 0

        Clock.schedule_interval(self._tick_gps_fake, 1.5)
        print("🧪 GPS simulado iniciado")
    
    def _tick_gps_fake(self, dt):
        if self._fake_index >= len(self.ruta_fake):
            return False  # detener simulación

        lat, lon = self.ruta_fake[self._fake_index]
        self._fake_index += 1

        # Simula callback de plyer GPS
        self.on_location_en_curso(
            lat=lat,
            lon=lon,
            speed=5.0,   # m/s (~18 km/h)
            bearing=90   # opcional
        )


# ==============================
# APLICACIÓN TARIFA
# ==============================
class TarifaScreen(Screen):
    def on_pre_enter(self):
        self.cargar_ofertas()

    def cargar_ofertas(self):
        """Carga las ofertas de mototaxistas para el viaje activo del pasajero"""
        layout = self.ids.tarifas_container
        layout.clear_widgets()

        try:
            headers = get_headers()

            #Obtener el viaje activo del pasajero
            resp_viajes = requests.get(f"{API_URL}/viajes/", headers=headers)
            if resp_viajes.status_code != 200:
                layout.add_widget(Label(text="Error al obtener viajes."))
                return

            viajes = resp_viajes.json()
            
            viajes_en_curso = next(
                (v for v in viajes if v["estado"] in ["en_curso"]),
                None
            )

            if viajes_en_curso:
                viaje_screen = self.manager.get_screen("viaje_en_curso")
                viaje_screen.cargar_viaje_en_curso()
                self.manager.current = "viaje_en_curso"
                
            viaje_activo = next(
                (v for v in viajes if v["estado"] in ["pendiente"]),
                None
            )

            if not viaje_activo:
                layout.add_widget(Label(text="No tienes viajes activos."))
                return

            viaje_id = viaje_activo["id"]

            #Obtener las ofertas relacionadas al viaje
            resp_ofertas = requests.get(f"{API_URL}/ofertas/", headers=headers)
            if resp_ofertas.status_code != 200:
                layout.add_widget(Label(text="Error al cargar ofertas."))
                return

            ofertas = [o for o in resp_ofertas.json() if o["viaje"] == viaje_id]

            if not ofertas:
                layout.add_widget(
                    Label(
                        text="Aún no hay ofertas de mototaxistas.\nEsperando ofertas.",
                        halign='center',
                        valign='middle',
                        text_size=(400, None),
                        size_hint_y=None
                          ))
                return

            for o in ofertas:

                card = MDCard(
                    orientation="vertical",
                    padding=15,
                    spacing=10,
                    size_hint_y=None,
                    height=180,
                    radius=14,
                    md_bg_color=(0.98, 0.97, 0.95, 1),
                    elevation=0,
                    shadow_softness = 0,
                    shadow_color = (0,0,0,0),
                )

                card.add_widget(MDLabel(
                    text = "Oferta",
                    theme_text_color = "Custom",
                    text_color = (1, 0.85, 0, 1)
                ))

                content_container = MDBoxLayout(
                    orientation = 'horizontal',
                    spacing = 5,
                )

                content = MDBoxLayout(
                    orientation = "vertical",
                    spacing = 5,

                )

                content.add_widget(MDLabel(
                    text=f"Mototaxista: [b]{o['mototaxista_nombre']}[/b]",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content.add_widget(MDLabel(
                    text=f"Tarifa sugerida: [b]{o['monto']}[/b]",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content.add_widget(MDLabel(
                    text=f"Tiempo estimado: [b]{o['tiempo_estimado']}[/b]",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content_container.add_widget(content)
                content_container.add_widget( Image(
                        source="assets/user_placeholder.png",
                        allow_stretch=True,   # se adapta al contenedor
                        keep_ratio=True,
                        size_hint = (None, None),
                        size = (80, 80),
                    ))
                

                
                card.add_widget(content_container)

                btn_box = BoxLayout(size_hint_y=None, height=40, spacing=10)
                
                btn_box.add_widget(MDRaisedButton(
                    text="Aceptar",
                    md_bg_color=(0.2, 0.2, 0.2, 1),
                    on_release=lambda x, oferta=o: self.aceptar_oferta(oferta)
                ))
                btn_box.add_widget(MDRectangleFlatButton(
                    text="Rechazar",
                    text_color=(1, 0.2, 0.2, 1),
                    line_color=(1, 0.2, 0.2, 1),
                    on_release=lambda x, oferta=o: self.rechazar_oferta(oferta)
                ))

                card.add_widget(btn_box)
                layout.add_widget(card)

        except Exception as e:
            layout.add_widget(Label(text=f"Error de conexión: {e}"))

    def aceptar_oferta(self, oferta):
        """El pasajero acepta una oferta y se asigna el mototaxista al viaje"""
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()
            headers = {"Authorization": f"Bearer {token}"}

            oferta_id = oferta["id"]
            resp = requests.patch(f"{API_URL}/ofertas/{oferta_id}/aceptar/", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                viaje_id = data.get("viaje_id")

                # ✅ Guardar el ID del viaje aceptado
                with open("viaje_actual.txt", "w") as f:
                    f.write(str(viaje_id))

                # 🔹 Cambiar de pantalla y mostrar detalles
                viaje_en_curso_screen = self.manager.get_screen("viaje_en_curso")
                viaje_en_curso_screen.cargar_viaje_en_curso()
                self.manager.current = "viaje_en_curso"

            else:
                self.ids.mensaje_tarifas.text = f"❌ Error al aceptar: {resp.text}"

        except Exception as e:
            self.ids.mensaje_tarifas.text = f"Error de conexión: {e}"

    def rechazar_oferta(self, oferta):
        """El pasajero rechaza una oferta"""
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}
            oferta_id = oferta["id"]

            resp = requests.delete(f"{API_URL}/ofertas/{oferta_id}/", headers=headers)

            if resp.status_code in [200, 204]:
                self.ids.mensaje_tarifas.text = "Oferta rechazada."
                self.cargar_ofertas()
            else:
                self.ids.mensaje_tarifas.text = f"Error: {resp.text}"

        except Exception as e:
            self.ids.mensaje_tarifas.text = f"Error de conexión: {e}"

# ==============================
# APLICACIÓN PRINCIPAL
# ==============================
class KooneexApp(MDApp):
    def build(self):
        # Registrar tipografías personalizadas
        LabelBase.register(name="Poppins", fn_regular="fonts/Poppins-Medium.ttf")
        LabelBase.register(name="Inter", fn_regular="fonts/Inter-Regular.ttf")
        Builder.load_file("kooneex.kv")
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(ViajeScreen(name="viaje"))
        sm.add_widget(PendientesScreen(name="pendientes"))
        sm.add_widget(TarifaScreen(name="tarifas"))
        sm.add_widget(ViajeEnCursoScreen(name="viaje_en_curso"))
        sm.add_widget(ViajeAceptadoMotoScreen(name="viaje_aceptado_moto"))
        sm.add_widget(ViajeEnCursoMotoScreen(name="viaje_en_curso_moto"))
        return sm


if __name__ == "__main__":
    KooneexApp().run()

