import requests
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty
from config import API_URL
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.menu import MDDropdownMenu
from kivy.utils import platform
import os
from helpers import get_headers
import re
from kivy.properties import BooleanProperty
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton

class RegistroScreen(MDScreen):
    username = StringProperty("")
    nombre = StringProperty("")
    apellido = StringProperty("")
    correo = StringProperty("")
    telefono = StringProperty("")
    password = StringProperty("")
    rol = StringProperty("pasajero")  # valor por defecto
    mensaje = StringProperty("")
    foto_path = None
    foto_cargada = BooleanProperty(False)
    dialog = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.file_manager = MDFileManager(
            exit_manager=self.cerrar_filemanager,
            select_path=self.seleccionar_path,
            preview=False,
        )
    
    def mostrar_error(self, mensaje):
        if not self.dialog:
            self.dialog = MDDialog(
                title="Error",
                text=mensaje,
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: self.cerrar_dialogo()
                    )
                ],
            )
        else:
            self.dialog.text = mensaje

        self.dialog.open()

    def cerrar_dialogo(self):
        self.dialog.dismiss()
    
    def abrir_menu_roles(self):
        items = [
            {
                "text": "Pasajero",
                "on_release": lambda x="pasajero": self.seleccionar_rol(x),
            },
            {
                "text": "Mototaxista",
                "on_release": lambda x="mototaxista": self.seleccionar_rol(x),
            },
        ]

        self.menu_roles = MDDropdownMenu(
            caller=self.ids.rol_input,
            items=items,
            width_mult=4,
            position = "center"
        )
        self.menu_roles.open()

    def seleccionar_rol(self, rol):
        self.rol = rol
        self.ids.rol_input.text = rol.capitalize()
        self.menu_roles.dismiss()
    
    def seleccionar_foto(self):
        if platform == "android":
            self.abrir_camara()
        else:
            start_path = "/"
            self.file_manager.show(start_path)
    
    def abrir_camara(self):
        try:
            # Ruta donde se guardará la imagen
            nombre = f"foto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            ruta = f"/storage/emulated/0/DCIM/{nombre}"

            camera.take_picture(
                filename=ruta,
                on_complete=self.foto_tomada
            )

        except Exception as e:
            print("❌ Error abriendo cámara:", e)

    def foto_tomada(self, path):
        """Se ejecuta cuando el usuario toma la foto"""
        if not path or not os.path.exists(path):
            print("❌ Foto no tomada")
            return

        print("📸 Foto guardada en:", path)
        self.foto_path = path
        # Mostrar preview
        self.foto_cargada = True

    def cerrar_filemanager(self, *args):
        self.file_manager.close()

    def seleccionar_path(self, path):
        """Se ejecuta al seleccionar un archivo"""
        self.cerrar_filemanager()

        if not self.es_imagen(path):
            print("❌ No es una imagen")
            return
        self.foto_path = path
        self.foto_cargada = True
        print("📸 Imagen seleccionada:", path)

    def es_imagen(self, path):
        extensiones = (".png", ".jpg", ".jpeg", ".webp")
        return path.lower().endswith(extensiones)
    
    #Validaciones del formulario
    def validar_telefono(self, telefono):
        return telefono.isdigit() and len(telefono) == 10
    
    def validar_email(self, email):
        patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        return re.match(patron, email) is not None
    
    def registrar(self):
        if not self.foto_cargada or not self.foto_path:
            self.mostrar_error("Debes tomar o seleccionar una foto antes de registrarte.")
            return
        
        files = {
            "foto": open(self.foto_path, "rb")
        }

        datos = {
            "username": self.username,
            "first_name":self.nombre,
            "last_name":self.apellido,
            "email":self.correo,
            "telefono":self.telefono,
            "password": self.password,
            "rol": self.rol
        }

        try:
            if not self.validar_telefono(self.telefono):
                self.mostrar_error("El teléfono debe tener 10 dígitos numéricos")
                return
                #self.mensaje = "El teléfono debe tener 10 dígitos numéricos"
            
            elif not self.validar_email(self.correo):
                self.mostrar_error("Correo electrónico inválido")
                #self.mensaje = "Correo electrónico inválido"
                return

            else:
                resp = requests.post(
                    f"{API_URL}/usuarios/registro/",
                    data=datos,
                    files=files,
                    timeout=10
                )

                if resp.ok:
                    self.mensaje = "Usuario creado correctamente"
                    self.manager.current = "login"
                else:
                    self.mensaje = resp.json().get(
                        "error", "Error al crear usuario"
                    )

        except Exception as e:
            self.mensaje = f"Error de conexión: {e}"


