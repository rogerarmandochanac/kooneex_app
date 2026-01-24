import requests
from helpers import get_headers
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.image import Image
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton, MDIconButton
from config import API_URL

class PendientesScreen(MDScreen):
    """Esta pantalla es para los viajes pendientes en la pantalla del mototaxista"""
    def cargar_viajes_pendientes(self):
        layout = self.ids.viajes_container
        try:
            headers = get_headers()
            resp = requests.get(f"{API_URL}/viajes/", headers=headers)

            
            layout.clear_widgets()

            if resp.status_code != 200:
                layout.add_widget(MDLabel(text="Error al cargar viajes.", theme_text_color="Error"))
                return

            viajes = resp.json()
            if not viajes:
                layout.padding = [24, 24, 24, 24]
                layout.add_widget(MDLabel(text="No hay viajes pendientes.", halign="center"))
                return

            for v in viajes:
                card = MDCard(
                    orientation="vertical",
                    padding=15,
                    spacing=10,
                    size_hint_y=None,
                    height=250,
                    radius=14,
                    md_bg_color=(0.98, 0.97, 0.95, 1),
                    elevation=0,
                    shadow_softness = 0,
                    shadow_color = (0,0,0,0),
                )
                
                content_container = MDBoxLayout(
                    orientation = 'horizontal',
                    spacing = 5,
                )

                content = MDBoxLayout(
                    orientation = "vertical",
                    spacing = 5,

                )

                content.add_widget(MDLabel(
                    text=f"Usuario: [b]{v['pasajero_nombre']}[/b]",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content.add_widget(MDLabel(
                    text=f"Pasajeros: [b]{v.get('cantidad_pasajeros', 1)}[/b]",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content.add_widget(MDLabel(
                    text=f"Tarifa sugerida: [b]${v.get('costo_estimado', 0)}[b]",
                    markup = True,
                    theme_text_color="Secondary"
                ))

                content.add_widget(MDLabel(
                    text=f"Distancia: [b]{v.get('distancia_km', 0)}[b] km",
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

                # -------- CAMPO TARIFA ---------
                tarifa_input = MDTextField(
                    hint_text="Tu tarifa (opcional)",
                    text=str(v.get("costo_estimado", "")),
                    mode="rectangle",
                    size_hint_y=None,
                    height=60
                )
                card.add_widget(tarifa_input)

                # -------- BOTONES ----------
                btn_box = MDBoxLayout(size_hint_y=None, height=55, spacing=10)

                btn_box.add_widget(MDRaisedButton(
                    text="Sugerir tarifa",
                    md_bg_color=(0.2, 0.2, 0.2, 1),
                    on_release=lambda x, vid=v["id"], tinput=tarifa_input:
                        self.sugerir_tarifa(vid, tinput.text)
                ))

                card.add_widget(btn_box)

                layout.add_widget(card)

        except Exception as e:
            layout.clear_widgets()
            layout.add_widget(MDLabel(text=f"Error: {e}", theme_text_color="Error"))

    
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
                
                # Bloquear botones y mostrar mensaje
                self.mostrar_espera_respuesta(viaje_id)

            else:
                print("Error al sugerir tarifa:", resp.text)

        except Exception as e:
            print("Error de conexión:", e)

    def rechazar_oferta(self, viaje_id):
        """El mototaxista rechaza la oferta de viaje."""
        try:
            headers = get_headers()
            datos = {"desicion": "rechazar"}
            resp = requests.delete(f"{API_URL}/ofertas/{viaje_id}/rechazar/", json=datos, headers=headers)

            if resp.status_code in [200, 202]:
                self.cargar_viajes_pendientes()
            else:
                print("Error al rechazar viaje:", resp.text)
        except Exception as e:
            print("Error de conexión:", e)
    
    def mostrar_espera_respuesta(self, viaje_id):
        layout = self.ids.viajes_container
        layout.clear_widgets()

        # --- Card principal ---
        card = MDCard(
            orientation="vertical",
            size_hint_y=None,
            height=260,
            padding=20,
            spacing=15,
            radius=[0],
            elevation=0,
            md_bg_color=(1, 1, 1, 1),   # Blanco elegante
        )

        # --- Encabezado con icono ---
        header = MDBoxLayout(
            orientation="horizontal",
            spacing=15,
            size_hint_y=None,
            height=40
        )

        header.add_widget(MDIconButton(
        icon="clock-outline",
        theme_text_color="Custom",
        text_color=(0.15, 0.15, 0.15, 1),
        disabled=True,                # Para que no parezca botón clickeable
        icon_size="36sp"
        ))

        header.add_widget(MDLabel(
            text=f"Oferta pendiente",
            font_style="H6",
            bold=True,
            theme_text_color="Primary"
        ))

        card.add_widget(header)

        # Separador elegante
        card.add_widget(MDBoxLayout(
        size_hint_y=None,
        height=1,
        md_bg_color=(0.85, 0.85, 0.85, 1)
    ))

        # --- Mensajes principales ---
        card.add_widget(MDLabel(
            text=f"Has enviado una oferta para el viaje",
            font_style="Body1",
            theme_text_color="Primary"
        ))

        card.add_widget(MDLabel(
            text="Esperando respuesta del pasajero...",
            font_style="Body2",
            theme_text_color="Secondary"
        ))

        # --- Espacio antes del botón ---
        card.add_widget(MDLabel(text="", size_hint_y=None, height=10))

        # --- Botón centrado ---
        btn = MDRaisedButton(
            text="Cancelar oferta",
            md_bg_color=(0.85, 0.25, 0.15, 1),  # Rojo quemado que combina
            text_color=(1, 1, 1, 1),
            elevation=0,
            pos_hint={"center_x": 0.5},
            on_release=lambda x: self.rechazar_oferta(viaje_id)
        )

        card.add_widget(btn)
        layout.add_widget(card)


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