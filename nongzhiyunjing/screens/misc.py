from utils import BaseScreen




class MapScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "map"
        self.setup_background("image/map.jpg")

    def on_touch_down(self, touch):
        if self.is_in_relative_area(touch.x, touch.y, (0.0, 0.865, 0.2, 1.0)):
            self.manager.current = "home"
        return True
