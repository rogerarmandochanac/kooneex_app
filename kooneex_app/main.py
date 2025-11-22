import requests
from kivy.app import App
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
from kivymd.uix.button import MDRectangleFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.image import Image
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivy.clock import mainthread
from kivy_garden.mapview import MapView, MapMarkerPopup
import requests
from kivy.clock import Clock, mainthread
from kivy_garden.mapview import MapMarker

Window.size = (360, 640)

API_URL = "http://127.0.0.1:8000/api"


LUGARES = {
    "Casa": (19.4326, -99.1332),
    "Trabajo": (19.44, -99.15),
    "Terminal": (19.4280, -99.10),
    "Centro": (19.45, -99.14),
}

# ==============================
# PANTALLA DE LOGIN
# ==============================
class LoginScreen(MDScreen):
    username = StringProperty("")
    password = StringProperty("")
    mensaje = StringProperty("")
    show_password = BooleanProperty(False)

    def toggle_password_visibility(self):
        """Alterna entre mostrar y ocultar la contraseña."""
        self.show_password = not self.show_password

    def login(self):
        datos = {"username": self.username, "password": self.password}
        try:
            resp = requests.post(f"{API_URL}/token/", json=datos)
            if resp.ok:               
                access_token = resp.json().get("access")

                # Guardar token
                headers = save_headers(access_token)
                
                #obtenemos el usuario actual logeado
                user_resp = requests.get(f"{API_URL}/usuario/", headers=headers)

                if resp.ok:
                    rol = user_resp.json().get("rol")

                    if rol == "pasajero":
                        self.evaluar_estado_del_viaje_pasajero(access_token)
                    
                    elif rol == "mototaxista":
                        self.manager.current = "pendientes"
                    
                    else:
                        self.mensaje = "Rol desconocido."
                
                else:
                    self.mensaje = "Error al obtener usuario."
            
            else:
                self.mensaje = "Credenciales incorrectas"
        
        except Exception as e:
            self.mensaje = f"Error de conexión: {e}"

    def evaluar_estado_del_viaje_pasajero(self, token):
        try:
            resp = requests.get(f"{API_URL}/viajes/obtener_estados_activos_pasajero/", headers=get_headers())
            estado = resp.json().get("estado")
            if resp.ok:
                if estado in ['aceptado', 'en_curso']:
                    viaje_en_curso_screen = self.manager.get_screen("viaje_en_curso")
                    viaje_en_curso_screen.cargar_viaje_en_curso()
                    self.manager.current = "viaje_en_curso"
                elif estado == 'pendiente':
                    self.manager.current = 'tarifas'
                    return
            elif resp.status_code == 500:
                self.manager.current = 'viaje'
            else:
                print("Error al verificar viajes:", resp.text)
                self.manager.current = "viaje"

        except Exception as e:
            print("Error al verificar viaje activo:", e)
            self.manager.current = "viaje"

# ==============================
# PANTALLA PASAJERO
# ==============================
class ViajeScreen(Screen):
    mapview = ObjectProperty(None)
    origen_seleccionado = BooleanProperty(False)
    mensaje = StringProperty("")
    buscar_evento = None
    origen_marker = None
    destino_marker = None

    def buscar_direccion(self, texto, tipo):
        """Evita saturar el servidor → aplica debounce 0.4 s."""
        if self.buscar_evento:
            self.buscar_evento.cancel()

        # esperar para que el usuario termine de escribir
        self.buscar_evento = Clock.schedule_once(
            lambda dt: self._ejecutar_busqueda(texto, tipo), 0.4
        )

    def _ejecutar_busqueda(self, texto, tipo):
        if len(texto) < 3:
            return  # no buscar texto demasiado corto

        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": texto,
                "format": "json",
                "limit": 1
            }
            headers = {"User-Agent": "Kooneex-App"}
            resp = requests.get(url, params=params, headers=headers)

            if resp.status_code != 200:
                return
            
            data = resp.json()
            if not data:
                return

            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])

            self._actualizar_mapa(tipo, lat, lon)

        except Exception as e:
            print("Error buscando dirección:", e)

    @mainthread
    def _actualizar_mapa(self, tipo, lat, lon):
        """Mover mapa y colocar marcador."""
        self.ids.mapa.center_on(lat, lon)

        if tipo == "origen":
            if self.origen_marker:
                self.ids.mapa.remove_widget(self.origen_marker)

            self.origen_marker = MapMarker(lat=lat, lon=lon)
            self.ids.mapa.add_widget(self.origen_marker)

            self.origen_lat = lat
            self.origen_lon = lon


        elif tipo == "destino":
            if self.destino_marker:
                self.ids.mapa.remove_widget(self.destino_marker)

            self.destino_marker = MapMarker(lat=lat, lon=lon)
            self.ids.mapa.add_widget(self.destino_marker)

            self.destino_lat = lat
            self.destino_lon = lon

    def on_enter(self, *args):
        """
        Crear mapa dentro de mapa_holder
        """
        if not hasattr(self, "mapa"):
            # Crear el mapa Kivy
            self.mapa = MapView(
                zoom=15,
                lat=19.4326,
                lon=-99.1332
            )

            # Insertarlo en el contenedor definido en KV
            # self.ids.mapa_holder.clear_widgets()
            # self.ids.mapa_holder.add_widget(self.mapa)

            # Vincular eventos
            self.mapa.bind(on_touch_up=self._on_map_touch)

        # Verificar viaje activo
        try:
            self.verificar_viaje_en_curso()
        except Exception as e:
            print("Error verificando viaje:", e)

    def _on_map_touch(self, instance, touch):
        """
        Detectar clic real sobre el mapa.
        """
        # Verificar que el clic es dentro del mapa, no en el screen entero
        if not self.mapa.collide_point(*touch.pos):
            return False

        # Solo clic izquierdo
        if hasattr(touch, "button") and touch.button != "left":
            return False

        # Convertir coordenadas del clic a lat/lon
        lat, lon = self.mapa.get_latlon_at(*touch.pos)
        self._on_map_click(lat, lon)
        return True

    @mainthread
    def _on_map_click(self, lat, lon):
        """
        Primer clic → ORIGEN
        Segundo clic → DESTINO
        """
        # Primer clic → origen
        if not self.origen_seleccionado:
            self.origen_lat = lat
            self.origen_lon = lon
            self.origen_seleccionado = True
            self._poner_marcador_origen(lat, lon)
            return

        # Segundo clic → destino
        self.destino_lat = lat
        self.destino_lon = lon
        self._poner_marcador_destino(lat, lon)

    def _poner_marcador_origen(self, lat, lon):
        if hasattr(self, "origen_marker"):
            self.mapa.remove_widget(self.origen_marker)

        self.origen_marker = MapMarkerPopup(lat=lat, lon=lon)
        self.mapa.add_widget(self.origen_marker)

    def _poner_marcador_destino(self, lat, lon):
        if hasattr(self, "destino_marker"):
            self.mapa.remove_widget(self.destino_marker)

        self.destino_marker = MapMarkerPopup(lat=lat, lon=lon)
        self.mapa.add_widget(self.destino_marker)

    def reiniciar_seleccion(self):
        self.origen_seleccionado = False
        self.origen_lat = None
        self.origen_lon = None
        self.destino_lat = None
        self.destino_lon = None

        # Remover marcadores
        if hasattr(self, "origen_marker"):
            self.mapa.remove_widget(self.origen_marker)
        if hasattr(self, "destino_marker"):
            self.mapa.remove_widget(self.destino_marker)
    
    def on_pre_enter(self):
        self.verificar_viaje_en_curso()

    def verificar_viaje_activo(self):
        """Verifica si hay un viaje activo y redirige si existe"""
        try:
            headers = get_headers()
            
            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            if resp.status_code == 200:
                viajes = resp.json()
                viaje_activo = next((v for v in viajes if v['estado'] in ['aceptado', 'en_curso']), None)

                if viaje_activo:
                    # Hay un viaje activo, redirigir al screen de viaje en curso
                    viaje_screen = self.manager.get_screen("viaje_en_curso")
                    viaje_screen.mostrar_viaje(viaje_activo)
                    self.manager.current = "viaje_en_curso"
                else:
                    # No hay viaje activo, permitir solicitar viaje
                    self.ids.solicitud_container.disabled = False
                    self.ids.solicitud_container.opacity = 1
            else:
                self.ids.mensaje_label.text = f"Error al consultar viajes: {resp.status_code}"

        except Exception as e:
            self.ids.mensaje_label.text = f"Error de conexión: {e}"
    
    def verificar_viaje_en_curso(self):
        try:
            headers = get_headers()

            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            if resp.status_code == 200:
                viajes = resp.json()
                # Buscar viaje en curso
                viaje_curso = next((v for v in viajes if v['estado'] == 'en_curso'), None)

                if viaje_curso:
                    # Guardar id para usarlo en el screen
                    App.get_running_app().viaje_en_curso_id = viaje_curso['id']
                    self.manager.get_screen("viaje_en_curso").mostrar_viaje(viaje_curso)
                    self.manager.current = "viaje_en_curso"
                else:
                    # Ningún viaje en curso, mostrar formulario de solicitud
                    self.manager.current = "viaje"
        except Exception as e:
            print("Error al verificar viaje en curso:", e)


    def solicitar_viaje(self):
        try:
            if not self.origen_lat or not self.origen_lon:
                self.mensaje = "Selecciona un origen válido."
                return

            if not self.destino_lat or not self.destino_lon:
                self.mensaje = "Selecciona un destino válido."
                return

            with open("token.txt", "r") as f:
                token = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}

            datos = {
                "origen_lat": float(self.origen_lat),
                "origen_lon": float(self.origen_lon),
                "destino_lat": float(self.destino_lat),
                "destino_lon": float(self.destino_lon),
                "cantidad_pasajeros": int(self.ids.cantidad_pasajeros.text),
            }

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
    def on_pre_enter(self):
        """Verifica si el mototaxista ya tiene una oferta activa o un viaje en curso."""
        try:
            headers = get_headers()
            # 1️ Verificar si tiene un viaje activo (aceptado o en curso) con el usuario que hace la peticion
            resp_viajes = requests.get(f"{API_URL}/viajes/verificar_viajes_activos/", headers=headers)
            if resp_viajes.status_code == 200:
                self.manager.get_screen("viaje_en_curso_moto").cargar_viaje_en_curso()
                self.manager.current = "viaje_en_curso_moto"
                return
            #Si no hay algun viaje aceptado o en curso
            elif resp_viajes.status_code == 204:
                # 2️ Verificar si el mototaxista ya envió una oferta
                resp_ofertas = requests.get(f"{API_URL}/viajes/verificar_viaje_ofertado/", headers=headers)
                if resp_ofertas.status_code == 200:
                    data_resp = resp_ofertas.json()
                    self.mostrar_espera_respuesta(data_resp.get('viaje_id', None))
                    return
                
                self.cargar_viajes_pendientes()
                return
            else:
                print("Error al obtener viajes:", resp_viajes.text)

            self.cargar_viajes_pendientes()

        except Exception as e:
            print("Error al verificar estado del mototaxista:", e)

    def cargar_viajes_pendientes(self):
        """Carga los viajes pendientes visibles para el mototaxista con estilo KivyMD."""
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

                # -------- DATOS DEL VIAJE ----------
                # card.add_widget(MDLabel(
                #     text=f"Viaje #{v['id']}",
                #     theme_text_color="Custom",
                #     text_color=(1, 0.85, 0, 1),
                #     font_style="H6"
                # ))
                
                content_container = MDBoxLayout(
                    orientation = 'horizontal',
                    spacing = 5,
                )

                content = MDBoxLayout(
                    orientation = "vertical",
                    spacing = 5,

                )

                content.add_widget(MDLabel(
                    text=f"Usuario: [b]{v['pasajero'].get('username')}[/b]",
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

                btn_box.add_widget(MDRectangleFlatButton(
                    text="Rechazar",
                    text_color=(1, 0.2, 0.2, 1),
                    line_color=(1, 0.2, 0.2, 1),
                    on_release=lambda x, vid=v["id"]:
                        self.rechazar_viaje(vid)
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

    def rechazar_viaje(self, viaje_id):
        """El mototaxista rechaza el viaje."""
        try:
            headers = get_headers()
            datos = {"desicion": "rechazar"}

            resp = requests.patch(f"{API_URL}/viajes/{viaje_id}/", json=datos, headers=headers)

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
            text=f"Has enviado una oferta para el viaje #{viaje_id}.",
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
            on_release=lambda x: self.rechazar_viaje(viaje_id)
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
                viaje_screen = self.manager.get_screen("viaje_en_curso_moto")
                viaje_screen.mostrar_viaje(viaje)
                self.manager.current = "viaje_en_curso_moto"
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

            if resp.status_code == 200:
                viaje = resp.json()
                if viaje:
                    viaje = viaje[0]
                    if viaje['estado'] == 'en_curso':
                        self.ids.info_label.text = f"Viaje en curso su mototaxista {viaje.get('mototaxista').get('username')} esta en camino"
                    else:
                        self.ids.info_label.text = (
                            f"Viaje {viaje['estado']} por el mototaxista {viaje.get('mototaxista').get('username')} con un costo final de ${viaje.get('costo_final')}"
                        )
            else:
                self.ids.info_label.text = "Error al cargar el viaje."

        except FileNotFoundError:
            self.ids.info_label.text = "No hay viaje activo."
        except Exception as e:
            self.ids.info_label.text = f"Error: {e}"


class ViajeEnCursoMotoScreen(Screen):
    def on_pre_enter(self):
        """Carga el viaje en curso del mototaxista al entrar en el screen"""
        self.cargar_viaje_en_curso()

    def cargar_viaje_en_curso(self):
        """Carga la información del viaje actual del mototaxista"""
        try:
            headers = get_headers()

            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            if resp.status_code == 200:
                viajes = resp.json()
                aceptado = next((v for v in viajes if v["estado"] in ["aceptado", "en_curso"]), None)

                if aceptado:
                    self.ids.info_label.text = (
                        f"Viaje #{aceptado['id']}\n"
                        f"Pasajero: {aceptado.get('pasajero').get('username')}\n"
                        f"Destino: {aceptado.get('destino_lat', 'N/A')}, {aceptado.get('destino_lon', 'N/A')}\n"
                        f"Tarifa: ${aceptado.get('costo_final', 'N/A')}\n"
                        f"Estado: {aceptado['estado']}"
                    )
                    if aceptado['estado'] == 'en_curso':
                        self.ids.btn_completar.disabled = False
                        self.ids.btn_iniciar.disabled = True
                    else:
                        self.ids.btn_completar.disabled = True
                        self.ids.btn_iniciar.disabled = False
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
                self.ids.info_label.text = "Viaje iniciado. En camino al destino."
                self.ids.btn_iniciar.disabled = True
                self.ids.btn_completar.disabled = False
            else:
                self.ids.info_label.text = f"❌ Error al iniciar: {resp.text}"

        except Exception as e:
            self.ids.info_label.text = f"Error: {e}"

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
            self.ids.info_label.text = f"Error: {e}"



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
        sm.add_widget(ViajeEnCursoMotoScreen(name="viaje_en_curso_moto"))
        return sm


if __name__ == "__main__":
    KooneexApp().run()

