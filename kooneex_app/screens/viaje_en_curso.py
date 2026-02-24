import requests
import websocket
import threading
import json
from kivymd.uix.screen import MDScreen
from config import API_URL
from helpers import get_headers
from kivy.animation import Animation
from kivy.graphics import Translate
from kivy.clock import Clock

class ViajeEnCursoScreen(MDScreen):
    """Pantalla pasajero donde se aprecia el viaje en curso"""
    viaje_id = None

    def conectar_websocket(self, viaje_id, token):
        url = f"ws://127.0.0.1:8000/ws/viaje/{viaje_id}/?token={token}"

        self.ws = websocket.WebSocketApp(
            url,
            on_message=self.on_ws_message,
            on_error=self.on_ws_error,
            on_close=self.on_ws_close
        )

        hilo = threading.Thread(target=self.ws.run_forever)
        hilo.daemon = True
        hilo.start()
    
    def on_ws_message(self, ws, message):
        data = json.loads(message)

        if data.get("type") == "estado_viaje":
            estado = data.get("estado")

            # 👇 Muy importante: actualizar UI en hilo principal
            Clock.schedule_once(lambda dt: self.actualizar_estado(estado, data))
    
    def on_ws_error(self, ws, error):
        print("Error WebSocket:", error)

    def on_ws_close(self, ws, close_status_code, close_msg):
        print("WebSocket cerrado")
        
    def actualizar_estado(self, estado, data):
        if estado == "en_curso":
            self.ids._spinner_en_curso.opacity = 0
            self.ids._spinner_en_curso.active = False

            self.ids.img_en_curso.opacity = 1
            self.animar_moto()

            self.ids.info_label.text = (
                f"El mototaxista [b]{data.get('mototaxista')}[/b] está en camino."
            )

        elif estado == "completado":
            self.ids.info_label.text = "Viaje completado ✅"
            self.ids.btn_completar.opacity = 0
    
    def on_pre_enter(self):
        viaje_id = self.viaje_id
        token = get_headers()["Authorization"].replace("Bearer ", "")

        self.conectar_websocket(viaje_id, token)

    def cargar_viaje_en_curso(self):
        
        """Carga la información del viaje en curso del pasajero"""
        try:
            headers = get_headers()

            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            if resp.ok:
                viaje = resp.json()
                if viaje:
                    viaje = viaje[0]
                    self.viaje_id = viaje.get('id')
                    if viaje['estado'] == 'en_curso':
                        self.ids.info_label.text = f"El mototaxista [b]{viaje.get('mototaxista_nombre')}[/b] esta en camino favor de estar pendiente."
                        self.ids.btn_completar.opacity = 1
                        self.ids._spinner_en_curso.opacity = 0
                        self.ids.img_en_curso.opacity = 1
                        self.animar_moto()
                    else:
                        self.ids.info_label.text = (
                            f"Solicitud enviada al mototaxista {viaje.get('mototaxista_nombre')}, esperando a que inicie el viaje."
                        )
                        self.ids.btn_completar.opacity = 0
                        self.ids._spinner_en_curso.opacity = 1
                        self.ids.img_en_curso.opacity = 0

            else:
                self.ids.info_label.text = "Error al cargar el viaje."

        except FileNotFoundError:
            self.ids.info_label.text = "No hay viaje activo."
        except Exception as e:
            self.ids.info_label.text = f"Error: {e}"
    
    def on_kv_post(self, base_widget):
        Clock.schedule_once(lambda dt: self.animar_moto(), 0)
    
    def animar_moto(self):
        img = self.ids.img_en_curso
        container = self.ids.anim_container

        img.x = -img.width

        def mover(*args):
            anim = Animation(
                x=container.width,
                duration=3,
                t='linear'
            )

            def reiniciar(*_):
                img.x = -img.width
                mover()

            anim.bind(on_complete=reiniciar)
            anim.start(img)

        mover()
    
    def marcar_completado(self):
        """Permite al pasajero marcar su viaje como completado"""
        try:
            headers = get_headers()
            datos = {"estado": "completado"}

            resp = requests.patch(f"{API_URL}/viajes/{self.viaje_id}/completar/", json=datos, headers=headers)

            if resp.status_code in [200, 202]:
                self.manager.current = "viaje"
            else:
                self.ids.info_label.text = f"❌ Error al completar: {resp.text}"

        except Exception as e:
            print(f'Error: {e}')
            #self.ids.info_label.text = f"Error: {e}"