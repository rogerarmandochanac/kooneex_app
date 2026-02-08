from kivy.lang import Builder
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager

from screens.login import LoginScreen
from screens.viaje import ViajeScreen
from screens.pendientes import PendientesScreen
from screens.tarifa import TarifaScreen
from screens.viaje_aceptado_moto import ViajeAceptadoMotoScreen
from screens.viaje_en_curso import ViajeEnCursoScreen
from screens.viaje_en_curso_moto import ViajeEnCursoMotoScreen
from screens.registro import RegistroScreen
from screens.espera_respuesta import EsperaRespuestaScreen

Window.size = (360, 640)


class KooneexApp(MDApp):
    def build(self):
        # Registrar tipografías personalizadas
        LabelBase.register(name="Poppins", fn_regular="fonts/Poppins-Medium.ttf")
        LabelBase.register(name="Inter", fn_regular="fonts/Inter-Regular.ttf")

        #Cargar archivos kv
        Builder.load_file("kooneex.kv")
        Builder.load_file("kv/login.kv")
        Builder.load_file("kv/registro.kv")
        Builder.load_file("kv/viaje.kv")
        Builder.load_file("kv/pendientes.kv")
        Builder.load_file("kv/tarifa.kv")
        Builder.load_file("kv/tarifa_item.kv")
        Builder.load_file("kv/viaje_aceptado_moto.kv")
        Builder.load_file("kv/viaje_en_curso.kv")
        Builder.load_file("kv/viaje_en_curso_moto.kv")
        Builder.load_file("kv/pendiente_item.kv")
        Builder.load_file("kv/espera_respuesta.kv")


        self.sm = MDScreenManager()
        
        #Agregamos los Screen al screen principal
        self.sm.add_widget(LoginScreen(name="login"))
        self.sm.add_widget(RegistroScreen(name="registro"))
        self.sm.add_widget(ViajeScreen(name="viaje"))
        self.sm.add_widget(PendientesScreen(name="pendientes"))
        self.sm.add_widget(TarifaScreen(name="tarifas"))
        self.sm.add_widget(ViajeEnCursoScreen(name="viaje_en_curso"))
        self.sm.add_widget(ViajeAceptadoMotoScreen(name="viaje_aceptado_moto"))
        self.sm.add_widget(ViajeEnCursoMotoScreen(name="viaje_en_curso_moto"))
        self.sm.add_widget(EsperaRespuestaScreen(name="espera_respuesta"))

        self.sm.current = "login"
        return self.sm

if __name__ == "__main__":
    KooneexApp().run()