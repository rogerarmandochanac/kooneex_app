from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty, NumericProperty
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.core.text import LabelBase
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from helpers import get_headers, save_headers
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.image import Image
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDRectangleFlatButton
from kivy_garden.mapview import MapView, MapMarkerPopup
from kivy.clock import Clock, mainthread
from kivy_garden.mapview import MapMarker, MapSource
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import OneLineListItem
from kivy.metrics import dp
from kivy.utils import platform
if platform == 'android':
    from plyer import gps
else:
    gps = None
from kivy.graphics import Color, Line

Window.size = (360, 640)

from screens.login import LoginScreen
from screens.viaje import ViajeScreen
from screens.pendientes import PendientesScreen
from screens.tarifa import TarifaScreen
from screens.viaje_aceptado_moto import ViajeAceptadoMotoScreen
from screens.viaje_en_curso import ViajeEnCursoScreen
from screens.viaje_en_curso_moto import ViajeEnCursoMotoScreen

class FlechaMarker(MapMarker):
    angle = NumericProperty(0)

class KooneexApp(MDApp):
    def build(self):
        # Registrar tipografías personalizadas
        LabelBase.register(name="Poppins", fn_regular="fonts/Poppins-Medium.ttf")
        LabelBase.register(name="Inter", fn_regular="fonts/Inter-Regular.ttf")
        Builder.load_file("kooneex.kv")
        Builder.load_file("kv/login.kv")
        Builder.load_file("kv/viaje.kv")
        Builder.load_file("kv/pendientes.kv")
        Builder.load_file("kv/tarifa.kv")
        Builder.load_file("kv/viaje_aceptado_moto.kv")
        Builder.load_file("kv/viaje_en_curso.kv")
        Builder.load_file("kv/viaje_en_curso_moto.kv")

        sm = ScreenManager()
        
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(ViajeScreen(name="viaje"))
        sm.add_widget(PendientesScreen(name="pendientes"))
        sm.add_widget(TarifaScreen(name="tarifas"))
        sm.add_widget(ViajeEnCursoScreen(name="viaje_en_curso"))
        sm.add_widget(ViajeAceptadoMotoScreen(name="viaje_aceptado_moto"))
        sm.add_widget(ViajeEnCursoMotoScreen(name="viaje_en_curso_moto"))
        return sm


if __name__ == "__main__":
    KooneexApp().run()

