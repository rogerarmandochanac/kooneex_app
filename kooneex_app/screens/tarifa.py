import requests
import websocket
import threading
import json

from helpers import get_headers
from config import API_URL

from kivy.app import App
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen

class TarifaScreen(MDScreen):
    "Pantalla del pasajero esperando o listando las ofertas"
    def conectar_ws_viaje(self):
        viaje_id = App.get_running_app().viaje_id
        ws_url = f"ws://127.0.0.1:8000/ws/viaje/{viaje_id}/"
        print("🧪 viaje_id:", viaje_id)

        if not viaje_id:
            print("❌ No hay viaje_id para conectar WS")
            return

        def on_message(ws, message):
            data = json.loads(message)
            tipo = data.get("type")

            if tipo == "nueva_oferta":
                print("💰 Nueva oferta:", data)
                Clock.schedule_once(lambda dt: self.cargar_ofertas())

            elif tipo == "oferta_cancelada":
                print("❌ Oferta cancelada recibida")
                Clock.schedule_once(lambda dt: self.cargar_ofertas())

        def on_open(ws):
            print("✅ WS conectado")

        def on_error(ws, error):
            print("❌ Error WS:", error)

        def on_close(ws, close_status_code, close_msg):
            print("🔴 WS cerrado")

        self.ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        hilo = threading.Thread(target=self.ws.run_forever)
        hilo.daemon = True
        hilo.start()
    
    def on_enter(self):
        Clock.schedule_once(self.cargar_ofertas, 0)

    def on_pre_enter(self):
        self.cargar_ofertas()
    
    def on_leave(self):
        if hasattr(self, "ws"):
            try:
                self.ws.close()
                print("🔌 WS cerrado manualmente")
            except:
                pass

            del self.ws

    def cargar_ofertas(self, dt=None):
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
            App.get_running_app().viaje_id = self.viaje_id

            if not hasattr(self, "ws"):
                self.conectar_ws_viaje()

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
        #Cancelamos la oferta
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
                App.get_running_app().viaje_id = None

                if hasattr(self, "ws"):
                    self.ws.close()
                    del self.ws

                self.manager.current = "viaje"

            else:
                self.ids.mensaje_tarifas.text = f"❌ No se pudo cancelar: {resp.text}"

        except Exception as e:
            self.ids.mensaje_tarifas.text = f"Error de conexión: {e}"