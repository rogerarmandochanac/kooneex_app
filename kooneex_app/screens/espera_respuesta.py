from kivymd.uix.screen import MDScreen
from kivy.properties import NumericProperty
from helpers import get_headers
import requests
from config import API_URL
from kivy.clock import Clock
import requests
import websocket
import threading
import json
from kivy.app import App

class EsperaRespuestaScreen(MDScreen):
    viaje_id = NumericProperty(None, allownone=True)
    
    def conectar_ws_mototaxi(self):
        viaje_id = self.viaje_id
        ws_url = f"ws://127.0.0.1:8000/ws/mototaxi/"
        print("🧪 viaje_id:", viaje_id)

        if not viaje_id:
            print("❌ No hay viaje_id para conectar WS")
            return

        def on_message(ws, message):
            data = json.loads(message)
            tipo = data.get("type")

            if tipo == "cancelar_viaje":
                print("❌ Viaje cancelado:")
                Clock.schedule_once(lambda dt: self.go_to_pendientes())
            

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
    
    def conectar_ws_viaje(self):
        viaje_id = self.viaje_id

        if not viaje_id:
            print("❌ No hay viaje_id")
            return

        ws_url = f"ws://127.0.0.1:8000/ws/viaje/{viaje_id}/"

        def on_message(ws, message):
            data = json.loads(message)
            tipo = data.get("type")

            if tipo == "oferta_aceptada":
                print("✅ Oferta aceptada")

                Clock.schedule_once(lambda dt: self.go_to_viaje_acpetado_moto())

        self.ws_viaje = websocket.WebSocketApp(
            ws_url,
            on_message=on_message
        )

        hilo = threading.Thread(target=self.ws_viaje.run_forever)
        hilo.daemon = True
        hilo.start()
    
    def on_enter(self):
        Clock.schedule_once(lambda dt: self.conectar_ws_mototaxi(), 0.2)
        Clock.schedule_once(lambda dt: self.conectar_ws_viaje(), 0.2)
    
    def on_leave(self):
        if hasattr(self, "ws"):
            try:
                self.ws.close()
                print("🔌 WS cerrado manualmente")
            except:
                pass
            del self.ws

    def go_to_pendientes(self):
        self.manager.current = "pendientes"
    
    def go_to_viaje_aceptado_moto(self):
        self.manager.current = "viaje_aceptado_moto"

    def rechazar_oferta(self):
        """El mototaxista rechaza la oferta de viaje."""
        try:
            headers = get_headers()
            datos = {"desicion": "rechazar"}
            resp = requests.delete(f"{API_URL}/ofertas/{self.viaje_id}/rechazar/", json=datos, headers=headers)

            if resp.status_code in [200, 202]:
                self.viaje_id = None
                App.get_running_app().viaje_id = None
                if hasattr(self, "ws"):
                    self.ws.close()
                    del self.ws
                self.manager.current = "pendientes"

            else:
                print("Error al rechazar viaje:", resp.text)
        except Exception as e:
            print("Error de conexión:", e)