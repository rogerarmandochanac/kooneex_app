import requests
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from functools import partial



Window.size = (360, 640)

API_URL = "http://127.0.0.1:8000/api"

# ==============================
# PANTALLA DE LOGIN
# ==============================
class LoginScreen(Screen):
    username = StringProperty("")
    password = StringProperty("")
    mensaje = StringProperty("")

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
                user_resp = requests.get(f"{API_URL}/usuario/", headers=headers)

                if user_resp.status_code == 200:
                    user_data = user_resp.json()
                    rol = user_data.get("rol")

                    # Guardar rol localmente
                    with open("rol.txt", "w") as f:
                        f.write(rol)

                    # 🔹 Verificación por rol
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

    # 🔍 Nueva función: verifica si el pasajero tiene viaje pendiente
    def verificar_viaje_activo(self, token):
        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            if resp.status_code == 200:
                viajes = resp.json()
                # Busca si hay viajes no terminados
                activos = [
                    v for v in viajes
                    if v['estado'] in ['pendiente', 'negociando', 'aceptado']
                ]

                if activos:
                    # 🚕 Si tiene uno, va a pantalla de tarifas
                    self.manager.current = "tarifas"
                else:
                    # 🟢 Si no, puede crear uno nuevo
                    self.manager.current = "viaje"
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

    def actualizar_estado_viaje(self, viaje_id):
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()
            
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{API_URL}/viajes/{viaje_id}/", headers=headers)

            if resp.status_code == 200:
                viaje = resp.json()
                self.ids.mensaje_label.text = (
                    f"Viaje #{viaje['id']} - Estado: {viaje['estado']}\n"
                    f"Mototaxista: {viaje['mototaxista'] or 'Sin asignar'}"
                )
            else:
                self.ids.mensaje_label.text = f"Error al consultar: {resp.status_code}"
        except Exception as e:
            self.ids.mensaje_label.text = f"Error: {e}"


# ==============================
# PANTALLA MOTOTAXISTA
# ==============================
class PendientesScreen(Screen):
    def on_pre_enter(self):
        self.cargar_viajes_pendientes()

    def cargar_viajes_pendientes(self):
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            layout = self.ids.viajes_container
            layout.clear_widgets()

            if resp.status_code == 200:
                viajes = resp.json()
                pendientes = [v for v in viajes if v['estado'] == 'pendiente']

                if not pendientes:
                    layout.add_widget(Label(text="No hay viajes pendientes.", color=(1,1,1,1)))
                else:
                    for v in pendientes:
                        card = BoxLayout(
                            orientation="vertical",
                            size_hint_y=None,
                            height=200,
                            padding=10,
                            spacing=5
                        )
                        card.add_widget(Label(text=f"🚖 Viaje #{v['id']}", bold=True, color=(1,1,0,1)))
                        card.add_widget(Label(text=f"Pasajeros: {v.get('cantidad_pasajeros', 1)}", color=(1,1,1,1)))
                        card.add_widget(Label(text=f"Costo sugerido: ${v.get('costo_estimado', 0)}", color=(1,1,1,1)))

                        tarifa_input = TextInput(
                            hint_text="Tu tarifa (opcional)",
                            input_filter="float",
                            multiline=False,
                            size_hint_y=None,
                            height=40,
                            text=v.get('costo_estimado')
                        )
                        card.add_widget(tarifa_input)

                        btn_box = BoxLayout(size_hint_y=None, height=40, spacing=10)
                        btn_box.add_widget(Button(
                            text="Sugerir tarifa",
                            background_color=(0,1,0,1),
                            on_release=lambda x, vid=v['id'], tinput=tarifa_input: self.sugerir_tarifa(vid, tinput.text)
                        ))
                        btn_box.add_widget(Button(
                            text="Rechazar",
                            background_color=(1,0,0,1),
                            on_release=lambda x, vid=v['id']: self.rechazar_viaje(vid)
                        ))

                        card.add_widget(btn_box)
                        layout.add_widget(card)
            else:
                layout.add_widget(Label(text="Error al cargar viajes.", color=(1,0,0,1)))

        except Exception as e:
            layout = self.ids.viajes_container
            layout.clear_widgets()
            layout.add_widget(Label(text=f"Error: {e}", color=(1,0,0,1)))

    def sugerir_tarifa(self, viaje_id, tarifa):
        """El mototaxista sugiere una tarifa personalizada"""
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}
            datos = {"estado": "negociando"}

            if tarifa:
                try:
                    datos["tarifa_sugerida"] = float(tarifa)
                except ValueError:
                    print("Tarifa no válida")

            resp = requests.patch(f"{API_URL}/viajes/{viaje_id}/", json=datos, headers=headers)

            if resp.status_code in [200, 202]:
                self.cargar_viajes_pendientes()
            else:
                print("Error al sugerir tarifa:", resp.text)
        except Exception as e:
            print("Error de conexión:", e)

    def rechazar_viaje(self, viaje_id):
        """El mototaxista rechaza el viaje"""
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

# --- TARIFASCREEN (PASAJERO) ---
class TarifaScreen(Screen):
    def on_pre_enter(self):
        self.cargar_tarifas()

    def cargar_tarifas(self):
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()

            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            layout = self.ids.tarifas_container
            layout.clear_widgets()

            if resp.status_code == 200:
                viajes = resp.json()
                # Filtrar viajes que están "negociando" o similares
                ofertas = [v for v in viajes if v['estado'] == 'negociando']
                if not ofertas:
                    layout.add_widget(Label(text="Aún no hay ofertas de mototaxistas."))
                else:
                    for v in ofertas:
                        card = BoxLayout(
                            orientation="vertical",
                            size_hint_y=None,
                            height=140,
                            padding=10,
                            spacing=5
                        )
                        card.add_widget(Label(text=f"Mototaxista: {v['mototaxista']}", color=(1,1,1,1)))
                        card.add_widget(Label(text=f"Tarifa sugerida: ${v.get('tarifa_sugerida', 0)}", color=(0,1,0,1)))

                        btn_box = BoxLayout(size_hint_y=None, height=40, spacing=10)
                        btn_box.add_widget(Button(
                            text="Aceptar",
                            background_color=(0,1,0,1),
                            on_release=lambda x, vid=v['id']: self.aceptar_tarifa(vid)
                        ))
                        btn_box.add_widget(Button(
                            text="Rechazar",
                            background_color=(1,0,0,1),
                            on_release=lambda x, vid=v['id']: self.rechazar_tarifa(vid)
                        ))

                        card.add_widget(btn_box)
                        layout.add_widget(card)
            else:
                layout.add_widget(Label(text="Error al cargar tarifas."))
        except Exception as e:
            layout.add_widget(Label(text=f"Error de conexión: {e}"))

    def aceptar_tarifa(self, viaje_id):
        self.actualizar_estado(viaje_id, "aceptado")

    def rechazar_tarifa(self, viaje_id):
        self.actualizar_estado(viaje_id, "cancelado")

    def actualizar_estado(self, viaje_id, estado):
        try:
            with open("token.txt", "r") as f:
                token = f.read().strip()
            headers = {"Authorization": f"Bearer {token}"}
            datos = {"estado": estado}
            resp = requests.patch(f"{API_URL}/viajes/{viaje_id}/", json=datos, headers=headers)

            if resp.status_code in [200, 202]:
                self.ids.mensaje_tarifas.text = "✅ Estado actualizado."
                self.cargar_tarifas()
            else:
                self.ids.mensaje_tarifas.text = f"❌ Error: {resp.text}"
        except Exception as e:
            self.ids.mensaje_tarifas.text = f"Error: {e}"

# ==============================
# APLICACIÓN PRINCIPAL
# ==============================
class KooneexApp(App):
    def build(self):
        Builder.load_file("kooneex.kv")
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(ViajeScreen(name="viaje"))
        sm.add_widget(PendientesScreen(name="pendientes"))
        sm.add_widget(TarifaScreen(name="tarifas"))
        return sm


if __name__ == "__main__":
    KooneexApp().run()

