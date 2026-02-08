import requests
from kivymd.uix.screen import MDScreen
from helpers import get_headers
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.fitimage import FitImage
from kivymd.uix.button import MDRaisedButton, MDIconButton
from config import API_URL

class TarifaScreen(MDScreen):
    viaje_id = None

    def on_pre_enter(self):
        self.cargar_ofertas()

    def cargar_ofertas(self):
        rv = self.ids.rv_ofertas
        rv.data = []

        try:
            headers = get_headers()

            resp_viajes = requests.get(f"{API_URL}/viajes/", headers=headers)
            if resp_viajes.status_code != 200:
                self.ids.mensaje_tarifas.text = "Error al obtener viajes."
                return

            viajes = resp_viajes.json()

            # Si ya hay viaje en curso → redirigir
            viaje_en_curso = next(
                (v for v in viajes if v["estado"] == "en_curso"),
                None
            )
            if viaje_en_curso:
                self.manager.get_screen("viaje_en_curso").cargar_viaje_en_curso()
                self.manager.current = "viaje_en_curso"
                return

            viaje_activo = next(
                (v for v in viajes if v["estado"] == "pendiente"),
                None
            )

            if not viaje_activo:
                self.ids.mensaje_tarifas.text = "No tienes viajes activos."
                return

            self.viaje_id = viaje_activo["id"]

            resp_ofertas = requests.get(f"{API_URL}/ofertas/", headers=headers)
            if resp_ofertas.status_code != 200:
                self.ids.mensaje_tarifas.text = "Error al cargar ofertas."
                return

            ofertas = [
                o for o in resp_ofertas.json()
                if o["viaje"] == self.viaje_id
            ]

            rv.data = [
                {
                    "oferta_id": o["id"],
                    "mototaxista_nombre": o["mototaxista_nombre"],
                    "monto": o["monto"],
                    "tiempo_estimado": o["tiempo_estimado"],
                    "mototaxista_foto": o.get("mototaxista_foto"),
                }
                for o in ofertas
            ]

        except Exception as e:
            self.ids.mensaje_tarifas.text = f"Error de conexión: {e}"

    def aceptar_oferta(self, oferta_id):
        try:
            headers = get_headers()
            resp = requests.patch(
                f"{API_URL}/ofertas/{oferta_id}/aceptar/",
                headers=headers
            )

            if resp.status_code == 200:
                viaje_id = resp.json().get("viaje_id")

                with open("viaje_actual.txt", "w") as f:
                    f.write(str(viaje_id))

                self.manager.get_screen("viaje_en_curso").cargar_viaje_en_curso()
                self.manager.current = "viaje_en_curso"
            else:
                self.ids.mensaje_tarifas.text = resp.text

        except Exception as e:
            self.ids.mensaje_tarifas.text = str(e)

    
    def eliminar_viaje(self, *args):
        if not self.viaje_id:
            return

        try:
            headers = get_headers()

            resp = requests.delete(
                f"{API_URL}/viajes/{self.viaje_id}/eliminar/",
                headers=headers
            )

            if resp.status_code in (200, 204):
                # Limpiar estado local
                self.viaje_id = None

                # (Opcional) borrar archivo local
                try:
                    import os
                    if os.path.exists("viaje_actual.txt"):
                        os.remove("viaje_actual.txt")
                except:
                    pass

                # 🔁 Volver a la pantalla de solicitud de viaje
                self.manager.current = "viaje"

            else:
                self.ids.mensaje_tarifas.text = f"❌ No se pudo cancelar: {resp.text}"

        except Exception as e:
            self.ids.mensaje_tarifas.text = f"Error de conexión: {e}"