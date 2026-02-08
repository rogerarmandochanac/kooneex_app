import requests
from helpers import get_headers
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.image import AsyncImage
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDIconButton
from config import API_URL
from kivymd.uix.fitimage import FitImage
from kivymd.uix.card import MDCard
from kivy.properties import StringProperty, NumericProperty

class PendienteItem(MDCard):
    viaje_id = NumericProperty()
    pasajero_nombre = StringProperty()
    pasajero_foto = StringProperty()
    cantidad_pasajeros = NumericProperty(1)
    costo_estimado = StringProperty("")
    distancia_km = StringProperty("")

    def sugerir(self):
        screen = self.parent.parent.parent.parent
        screen.sugerir_tarifa(self.viaje_id, self.costo_estimado)

class PendientesScreen(MDScreen):
    """Esta pantalla es para los viajes pendientes en la pantalla del mototaxista"""

    def on_enter(self):
        from kivy.clock import Clock
        Clock.schedule_once(self.cargar_viajes_pendientes, 0)

    def cargar_viajes_pendientes(self, dt=None):
        rv = self.ids.rv_viajes
        rv.data = []

        headers = get_headers()
        resp = requests.get(f"{API_URL}/viajes/", headers=headers)

        if resp.status_code != 200:
            return

        viajes = resp.json()

        rv.data = [
            {
                "viaje_id": v["id"],
                "pasajero_nombre": v["pasajero_nombre"],
                "pasajero_foto": v.get("pasajero_foto"),
                "cantidad_pasajeros": v.get("cantidad_pasajeros", 1),
                "costo_estimado": str(v.get("costo_estimado", "")),
                "distancia_km": str(v.get("distancia_km", 0)),
            }
            for v in viajes
        ]

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
                screen = self.manager.get_screen("espera_respuesta")
                screen.viaje_id = viaje_id
                self.manager.current = "espera_respuesta"
            else:
                print("Error al sugerir tarifa:", resp.text)

        except Exception as e:
            print("Error de conexión:", e)

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