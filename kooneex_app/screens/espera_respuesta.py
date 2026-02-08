from kivymd.uix.screen import MDScreen
from kivy.properties import NumericProperty
from helpers import get_headers
import requests
from config import API_URL
from kivy.clock import Clock

class EsperaRespuestaScreen(MDScreen):
    viaje_id = NumericProperty(None)
    
    def rechazar_oferta(self):
        """El mototaxista rechaza la oferta de viaje."""
        try:
            headers = get_headers()
            datos = {"desicion": "rechazar"}
            resp = requests.delete(f"{API_URL}/ofertas/{self.viaje_id}/rechazar/", json=datos, headers=headers)

            if resp.status_code in [200, 202]:
                self.manager.current = "pendientes"

            else:
                print("Error al rechazar viaje:", resp.text)
        except Exception as e:
            print("Error de conexión:", e)