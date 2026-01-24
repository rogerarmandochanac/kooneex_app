import requests
from kivymd.uix.screen import MDScreen
from helpers import get_headers
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.image import Image
from kivymd.uix.button import MDRaisedButton, MDIconButton
from config import API_URL

class TarifaScreen(MDScreen):
    """Pantalla del pasajero que visualiza la lista de todas las ofertas de los mototaxistas"""
    viaje_id = None

    def on_pre_enter(self):
        self.cargar_ofertas()

    def cargar_ofertas(self):
        layout = self.ids.tarifas_container
        layout.clear_widgets()

        try:
            headers = get_headers()
            resp_viajes = requests.get(f"{API_URL}/viajes/", headers=headers)
            if resp_viajes.status_code != 200:
                layout.add_widget(MDLabel(text="Error al obtener viajes."))
                return

            viajes = resp_viajes.json()
            
            viajes_en_curso = next(
                (v for v in viajes if v["estado"] in ["en_curso"]),
                None
            )

            if viajes_en_curso:
                viaje_screen = self.manager.get_screen("viaje_en_curso")
                viaje_screen.cargar_viaje_en_curso()
                self.manager.current = "viaje_en_curso"
                
            viaje_activo = next(
                (v for v in viajes if v["estado"] in ["pendiente"]),
                None
            )

            if not viaje_activo:
                layout.add_widget(MDLabel(text="No tienes viajes activos."))
                return

            viaje_id = viaje_activo["id"]
            self.viaje_id = viaje_id

            #Obtener las ofertas relacionadas al viaje
            resp_ofertas = requests.get(f"{API_URL}/ofertas/", headers=headers)
            if resp_ofertas.status_code != 200:
                layout.add_widget(MDLabel(text="Error al cargar ofertas."))
                return

            ofertas = [o for o in resp_ofertas.json() if o["viaje"] == viaje_id]

            if not ofertas:
                layout.add_widget(
                    MDLabel(
                        text="Aún no hay ofertas de mototaxistas.\nEsperando ofertas.",
                        halign='center',
                        valign='middle',
                        text_size=(400, None),
                        size_hint_y=None
                          ))
                return

            for o in ofertas:
                card = MDCard(
                    orientation="vertical",
                    padding=15,
                    spacing=10,
                    size_hint_y=None,
                    height=180,
                    radius=14,
                    md_bg_color=(0.98, 0.97, 0.95, 1),
                    elevation=0,
                    shadow_softness = 0,
                    shadow_color = (0,0,0,0),
                )

                card.add_widget(MDLabel(
                    text = "Oferta",
                    theme_text_color = "Custom",
                    text_color = (1, 0.85, 0, 1)
                ))

                content_container = MDBoxLayout(
                    orientation = 'horizontal',
                    spacing = 5,
                )

                content = MDBoxLayout(
                    orientation = "vertical",
                    spacing = 5,

                )

                content.add_widget(MDLabel(
                    text=f"Mototaxista: [b]{o['mototaxista_nombre']}[/b]",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content.add_widget(MDLabel(
                    text=f"Tarifa sugerida: [b]{o['monto']}[/b]",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content.add_widget(MDLabel(
                    text=f"Tiempo estimado: [b]{o['tiempo_estimado']}[/b]",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content_container.add_widget(content)
                content_container.add_widget( Image(
                        source="assets/user_placeholder.png",
                        allow_stretch=True,   # se adapta al contenedor
                        keep_ratio=True,
                        size_hint = (None, None),
                        size = (80, 80),
                    ))
                

                
                card.add_widget(content_container)

                btn_box = MDBoxLayout(size_hint_y=None, height=40, spacing=10)
                
                btn_box.add_widget(MDRaisedButton(
                    text="Aceptar",
                    md_bg_color=(0.2, 0.2, 0.2, 1),
                    on_release=lambda x, oferta=o: self.aceptar_oferta(oferta)
                ))

                card.add_widget(btn_box)
                layout.add_widget(card)

        except Exception as e:
            layout.add_widget(MDLabel(text=f"Error de conexión: {e}"))

    def aceptar_oferta(self, oferta):
        """El pasajero acepta una oferta y se asigna el mototaxista al viaje"""
        try:
            headers = get_headers()
            oferta_id = oferta["id"]
            resp = requests.patch(f"{API_URL}/ofertas/{oferta_id}/aceptar/", headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                viaje_id = data.get("viaje_id")

                # ✅ Guardar el ID del viaje aceptado
                with open("viaje_actual.txt", "w") as f:
                    f.write(str(viaje_id))

                # 🔹 Cambiar de pantalla y mostrar detalles
                viaje_en_curso_screen = self.manager.get_screen("viaje_en_curso")
                viaje_en_curso_screen.cargar_viaje_en_curso()
                self.manager.current = "viaje_en_curso"

            else:
                self.ids.mensaje_tarifas.text = f"❌ Error al aceptar: {resp.text}"

        except Exception as e:
            self.ids.mensaje_tarifas.text = f"Error de conexión: {e}"
    
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