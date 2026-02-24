import requests
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty, BooleanProperty
from helpers import get_headers
from config import API_URL
from kivymd.uix.relativelayout import MDRelativeLayout
import websocket
import threading
import json
from kivy.app import App

class ClickableTextFieldRound(MDRelativeLayout):
    text = StringProperty()
    hint_text = StringProperty()

class LoginScreen(MDScreen):
    username = StringProperty("")
    password = StringProperty("")
    mensaje = StringProperty("")
    show_password = BooleanProperty(False)

    def toggle_password(self):
        print(self.show_password)
        self.show_password = not self.show_password
        

    def login(self):
        #Enviamos la data al API para poder logearnos
        datos = {"username": self.username, "password": self.password}
        try:
            resp = requests.post(f"{API_URL}/token/", json=datos, timeout=10)
            
            if resp.ok:               
                access_token = resp.json().get("access")
                App.get_running_app().token = access_token
                headers = {
                    "Authorization": f"Bearer {access_token}"
                }
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
                    viaje_id = data.get("viaje_id")
                    # 🔥 AQUI agregas esto
                    self.conectar_websocket(viaje_id)
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
            resp = requests.get(
                f"{API_URL}/viajes/verificar_viajes_activos/",
                headers=get_headers(),
                timeout=10
            )

            if not resp.ok:
                print("Error al obtener viajes:", resp.text)
                self.manager.current = "pendientes"

            data = resp.json()
            mensaje = data.get("mensaje")

            if mensaje == "tiene_viaje_aceptado":
                viaje_id = data.get("viaje_id")
                self.conectar_websocket(viaje_id)
                screen = self.manager.get_screen("viaje_aceptado_moto")
                screen.cargar_viaje_en_curso()
                self.manager.current = "viaje_aceptado_moto"

            elif mensaje == "tiene_viaje_en_curso":
                viaje_id = data.get("viaje_id")
                self.conectar_websocket(viaje_id)
                self.manager.current = "viaje_en_curso_moto"

            elif mensaje == "tiene_viaje_ofertado":
                screen = self.manager.get_screen("espera_respuesta")
                screen.viaje_id = data.get("viaje_id")
                self.manager.current = "espera_respuesta"

            else:  # None u otro valor
                self.manager.current = "pendientes"

        except requests.exceptions.RequestException as e:
            print("Error de red:", e)

        except Exception as e:
            print("Error al verificar estado del mototaxista:", e)
    
    def conectar_websocket(self, viaje_id):
        token = get_headers().get("Authorization").replace("Bearer ", "")

        ws_url = f"ws://127.0.0.1:8000/ws/viaje/{viaje_id}/?token={token}"

        def on_message(ws, message):
            print("📩 MENSAJE WS:", message)

        def on_open(ws):
            print("✅ WebSocket conectado")

        def on_close(ws, close_status_code, close_msg):
            print("❌ WebSocket cerrado")

        def on_error(ws, error):
            print("⚠️ Error WS:", error)

        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_open=on_open,
            on_close=on_close,
            on_error=on_error,
        )

        hilo = threading.Thread(target=self.ws.run_forever)
        hilo.daemon = True
        hilo.start()
