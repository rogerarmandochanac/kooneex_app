from kivy.uix.image import Image
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.properties import NumericProperty

class MotoIcon(Image):
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            PushMatrix()
            self.rot = Rotate()
            self.rot.axis = (0, 0, 1)

        with self.canvas.after:
            PopMatrix()

        self.bind(
            pos=self._update_origin,
            size=self._update_origin,
            angle=self._update_angle
        )

    def _update_origin(self, *args):
        self.rot.origin = self.center

    def _update_angle(self, *args):
        self.rot.angle = self.angle
