import requests
from kivymd.uix.screen import MDScreen
from config import API_URL
from helpers import get_headers


class ViajeAceptadoMotoScreen(MDScreen):
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
                        f"Oferta Aceptada por el pasajero {aceptado.get('pasajero_nombre')} "
                        f"con una distancia de {aceptado.get('distancia_km', 'N/A')} km.\n"
                        f"Total a cobrar: ${aceptado.get('costo_final', 'N/A')}\n"
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