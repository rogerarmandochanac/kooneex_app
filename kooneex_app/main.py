import requests
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, BooleanProperty
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.core.text import LabelBase

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

Window.size = (360, 640)

API_URL = "http://127.0.0.1:8000/api"

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
            if resp.status_code == 200:
                tokens = resp.json()
                access_token = tokens.get("access")

                # Guardar token
                with open("token.txt", "w") as f:
                    f.write(access_token)

                headers = {"Authorization": f"Bearer {access_token}"}
                #obtenemos el usuario actual logeado
                user_resp = requests.get(f"{API_URL}/usuario/", headers=headers)

                if user_resp.status_code == 200:
                    user_data = user_resp.json()
                    rol = user_data.get("rol")

                    # Guardar rol localmente
                    with open("rol.txt", "w") as f:
                        f.write(rol)

                    #Verificación por rol
                    if rol == "pasajero":
                        self.verificar_viaje_activo(access_token)
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

    # Verifica si el pasajero tiene viaje pendiente
    def verificar_viaje_activo(self, token):
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{API_URL}/viajes/verificar_viajes_activos/", headers=headers)
            data = resp.json()
            print(data)
            if resp.status_code == 200:
                if data['estado'] in ['aceptado', 'en_curso']:
                    viaje_en_curso_screen = self.manager.get_screen("viaje_en_curso")
                    viaje_en_curso_screen.cargar_viaje_en_curso()
                    self.manager.current = "viaje_en_curso"
                elif data['estado'] == 'pendiente':
                    self.manager.current = 'tarifas'
                    return
            elif resp.status_code == 204:
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
    mensaje = StringProperty("")

    def on_pre_enter(self):
        self.verificar_viaje_en_curso()

    def verificar_viaje_activo(self):
        """Verifica si hay un viaje activo y redirige si existe"""
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            if resp.status_code == 200:
                viajes = resp.json()
                viaje_activo = next((v for v in viajes if v['estado'] in ['pendiente','aceptado', 'en_curso']), None)

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
            with open("token.txt", "r") as f:
                token = f.read().strip()
            headers = {"Authorization": f"Bearer {token}"}
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


    def solicitar_viaje(self, origen_lat, origen_lon, destino_lat, destino_lon, cantidad_pasajeros):
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()
            headers = {"Authorization": f"Bearer {token}"}
            datos = {
                "origen_lat": float(origen_lat),
                "origen_lon": float(origen_lon),
                "destino_lat": float(destino_lat),
                "destino_lon": float(destino_lon),
                "cantidad_pasajeros": int(cantidad_pasajeros)
            }

            resp = requests.post(f"{API_URL}/viajes/", json=datos, headers=headers)
            if resp.status_code == 201:
                self.manager.current = "tarifas"
            else:
                self.ids.mensaje_label.text = f"Error: {resp.text}"

        except Exception as e:
            self.ids.mensaje_label.text = f"Error de conexión: {e}"

# ==============================
# PANTALLA MOTOTAXISTA DE SOLICITUD DE VIAJE
# ==============================
class PendientesScreen(Screen):
    def on_pre_enter(self):
        """Verifica si el mototaxista ya tiene una oferta activa o un viaje en curso."""
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()
            headers = {"Authorization": f"Bearer {token}"}

            # Obtener usuario autenticado
            user_info = requests.get(f"{API_URL}/usuario/", headers=headers)
            usuario = user_info.json().get("username") if user_info.status_code == 200 else None

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
                else:
                    print("Error al obtener ofertas:", resp_ofertas.text)
                self.cargar_viajes_pendientes()
                return
            else:
                print("Error al obtener viajes:", resp_viajes.text)

            self.cargar_viajes_pendientes()

        except Exception as e:
            print("Error al verificar estado del mototaxista:", e)

    def cargar_viajes_pendientes(self):
        """Carga los viajes pendientes visibles para el mototaxista."""
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            layout = self.ids.viajes_container
            layout.clear_widgets()

            if resp.status_code == 200:
                viajes = resp.json()
                #Obtener el nombre del usuario autenticado
                user_info = requests.get(f"{API_URL}/usuario/", headers=headers)
                if user_info.status_code == 200:
                    usuario = user_info.json().get("username")
                else:
                    usuario = None
                #No mostrar nada si el mototaxista ya tiene un viaje activo
                tiene_viaje_activo = any(
                    v.get("mototaxista") == usuario and v["estado"] in ["en_curso", "aceptado"]
                    for v in viajes
                )
                if tiene_viaje_activo:
                    self.manager.get_screen("viaje_en_curso_moto").cargar_viaje_en_curso()
                    self.manager.current = "viaje_en_curso_moto"
                    return

                #Filtrar viajes pendientes
                pendientes = [v for v in viajes if v["estado"] == "pendiente"]
                if not pendientes:
                    layout.add_widget(Label(text="No hay viajes pendientes.", color=(1, 1, 1, 1)))
                    return

                for v in pendientes:
                    card = BoxLayout(
                        orientation="vertical",
                        size_hint_y=None,
                        height=150,
                        padding=10,
                        spacing=5
                    )
                    card.add_widget(Label(text=f"Viaje #{v['id']}", color=(1, 1, 0, 1)))
                    card.add_widget(Label(text=f"Pasajeros: {v.get('cantidad_pasajeros', 1)}", color=(1, 1, 1, 1)))
                    card.add_widget(Label(text=f"Tarifa sugerida: ${v.get('costo_estimado', 0)}", color=(1, 1, 1, 1)))

                    tarifa_input = TextInput(
                        hint_text="Tu tarifa (opcional)",
                        input_filter="float",
                        multiline=False,
                        size_hint_y=None,
                        height=40,
                        text=str(v.get("costo_estimado", ""))
                    )
                    card.add_widget(tarifa_input)

                    btn_box = BoxLayout(size_hint_y=None, height=40, spacing=10)

                    btn_box.add_widget(Button(
                        text="Sugerir tarifa",
                        background_color=(0, 1, 0, 1),
                        on_release=lambda x, vid=v["id"], tinput=tarifa_input: self.sugerir_tarifa(vid, tinput.text)
                    ))
                    btn_box.add_widget(Button(
                        text="Rechazar",
                        background_color=(1, 0, 0, 1),
                        on_release=lambda x, vid=v["id"]: self.rechazar_viaje(vid)
                    ))

                    card.add_widget(btn_box)
                    layout.add_widget(card)

            else:
                layout.add_widget(Label(text="Error al cargar viajes.", color=(1, 0, 0, 1)))

        except Exception as e:
            layout.clear_widgets()
            layout.add_widget(Label(text=f"Error: {e}", color=(1, 0, 0, 1)))

    def sugerir_tarifa(self, viaje_id, tarifa):
        """El mototaxista sugiere una tarifa personalizada y bloquea otras opciones."""
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}
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
            with open("token.txt", "r") as f:
                token = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}
            datos = {"estado": "cancelado"}

            resp = requests.patch(f"{API_URL}/viajes/{viaje_id}/", json=datos, headers=headers)

            if resp.status_code in [200, 202]:
                self.cargar_viajes_pendientes()
            else:
                print("Error al rechazar viaje:", resp.text)
        except Exception as e:
            print("Error de conexión:", e)
    
    def mostrar_espera_respuesta(self, viaje_id):
        """Bloquea botones y muestra mensaje de espera después de sugerir tarifa."""
        layout = self.ids.viajes_container
        layout.clear_widgets()

        # Crear una sola tarjeta con mensaje
        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=200,
            padding=10,
            spacing=5
        )
        card.add_widget(Label(text=f"Oferta enviada para el viaje #{viaje_id}", color=(1, 1, 0, 1)))
        card.add_widget(Label(text="Esperando respuesta del pasajero...", color=(1, 1, 1, 1)))

        # Botón para cancelar la oferta
        cancelar_btn = Button(
            text="Cancelar oferta",
            background_color=(1, 0.5, 0, 1),
            size_hint_y=None,
            height=40,
            on_release=lambda x: self.cancelar_oferta(viaje_id)
        )
        card.add_widget(cancelar_btn)

        layout.add_widget(card)

    def iniciar_viaje(self, viaje_id):
        """Inicia el viaje y pasa al screen de viaje en curso."""
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}
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
            with open("token.txt", "r") as f:
                token = f.read().strip()
            headers = {"Authorization": f"Bearer {token}"}

            with open("viaje_actual.txt", "r") as f:
                viaje_id = f.read().strip()

            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            if resp.status_code == 200:
                viaje = resp.json()
                if viaje:
                    viaje = viaje[0]
                    self.ids.info_label.text = (
                        f"Viaje #{viaje['id']}\n"
                        f"Mototaxista: {viaje.get('mototaxista').get('username', 'None')}\n"
                        f"Tarifa:${viaje.get('costo_final')}\n"
                        f"Estado: {viaje['estado']}"
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
            with open("token.txt", "r") as f:
                token = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}
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
                self.ids.info_label.text = "✅ Viaje iniciado. En camino al destino."
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
            with open("token.txt", "r") as f:
                token = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}

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
                card = BoxLayout(
                    orientation="vertical",
                    size_hint_y=None,
                    height=140,
                    padding=10,
                    spacing=5
                )
                card.add_widget(Label(text=f"Mototaxista: {o['mototaxista_nombre']}", color=(1,1,1,1)))
                card.add_widget(Label(text=f"Tarifa sugerida: ${o['monto']}", color=(0,1,0,1)))
                card.add_widget(Label(text=f"Tiempo estimado: {o['tiempo_estimado']}", color=(1,1,1,1)))

                btn_box = BoxLayout(size_hint_y=None, height=40, spacing=10)
                btn_box.add_widget(Button(
                    text="Aceptar",
                    background_color=(0,1,0,1),
                    on_release=lambda x, oferta=o: self.aceptar_oferta(oferta)
                ))
                btn_box.add_widget(Button(
                    text="Rechazar",
                    background_color=(1,0,0,1),
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

