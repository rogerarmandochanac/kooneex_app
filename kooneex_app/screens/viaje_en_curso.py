import requests
from kivymd.uix.screen import MDScreen
from config import API_URL
from helpers import get_headers

class ViajeEnCursoScreen(MDScreen):
    """Pantalla pasajero donde se aprecia el viaje en curso"""
    viaje_id = None
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
                    else:
                        self.ids.info_label.text = (
                            f"Solicitud enviada al mototaxista {viaje.get('mototaxista_nombre')}, esperando a que inicie el viaje."
                        )
                        self.ids.btn_completar.opacity = 0
            else:
                self.ids.info_label.text = "Error al cargar el viaje."

        except FileNotFoundError:
            self.ids.info_label.text = "No hay viaje activo."
        except Exception as e:
            self.ids.info_label.text = f"Error: {e}"
    
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