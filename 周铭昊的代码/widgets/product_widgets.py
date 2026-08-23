from kivy.app import App
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.graphics import Color, Line
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from utils import text_style, show_toast
from widgets.base_widgets import GrayPlaceholder


class ProductRow(ButtonBehavior, BoxLayout):
    product_id = NumericProperty(0)
    name_text = StringProperty("")
    specification_text = StringProperty("")
    price_text = StringProperty("")
    sold_text = StringProperty("")
    from_tab_text = StringProperty("")
    return_screen_name = StringProperty("store_category")
    screen_ref = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", spacing=dp(12),
                         padding=(dp(14), dp(10)), **kwargs)
        self.size_hint_y = None
        self.height = dp(116)
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self._build_ui()

    def _build_ui(self):
        thumb_wrap = BoxLayout(size_hint=(None, None), size=(dp(80), dp(80)))
        thumb_wrap.add_widget(GrayPlaceholder(size_hint=(1, 1)))
        self.add_widget(thumb_wrap)

        info_box = BoxLayout(orientation="vertical", spacing=0, size_hint=(1, 1),
                             padding=(0, dp(8), 0, dp(10)))
        self.name_label = Label(text="", color=(0.1, 0.1, 0.1, 1), halign="left", valign="top",
                                font_size=sp(17), size_hint=(1, None), height=dp(50), **text_style())
        self.name_label.bind(size=self.name_label.setter("text_size"))
        info_box.add_widget(self.name_label)
        info_box.add_widget(Widget(size_hint=(1, None), height=dp(10)))
        self.meta_label = Label(text="", color=(0.42, 0.42, 0.42, 1), halign="left", valign="middle",
                                font_size=sp(13), size_hint=(1, None), height=dp(22), **text_style())
        self.meta_label.bind(size=self.meta_label.setter("text_size"))
        info_box.add_widget(self.meta_label)
        self.add_widget(info_box)

        right_box = BoxLayout(orientation="vertical", spacing=dp(8), size_hint=(None, 1),
                              width=dp(92), padding=(0, dp(12), 0, dp(12)))
        self.price_label = Label(text="", color=(0.88, 0.32, 0.18, 1), halign="right", valign="middle",
                                 font_size=sp(16), bold=True, size_hint=(1, None), height=dp(28), **text_style())
        self.price_label.bind(size=self.price_label.setter("text_size"))
        right_box.add_widget(self.price_label)
        self.sold_label = Label(text="", color=(0.45, 0.45, 0.45, 1), halign="right", valign="middle",
                                font_size=sp(12), size_hint=(1, None), height=dp(22), **text_style())
        self.sold_label.bind(size=self.sold_label.setter("text_size"))
        right_box.add_widget(self.sold_label)
        self.add_widget(right_box)
        self.refresh_view()

    def _update_canvas(self, *_args):
        self.canvas.before.clear()
        self.canvas.after.clear()
        with self.canvas.after:
            Color(0.90, 0.90, 0.90, 1)
            Line(points=[self.x, self.y, self.right, self.y], width=1)

    def refresh_view(self):
        self.name_label.text = self.name_text
        self.meta_label.text = self.specification_text
        self.price_label.text = self.price_text
        self.sold_label.text = self.sold_text

    def refresh_view_attrs(self, rv, index, data):
        result = super().refresh_view_attrs(rv, index, data)
        Clock.schedule_once(lambda dt: self.refresh_view(), 0)
        return result

    def on_release(self):
        try:
            app = App.get_running_app()
            if app and hasattr(app, "open_product_detail_screen") and self.product_id:
                app.open_product_detail_screen(
                    self.product_id,
                    from_tab=self.from_tab_text or "精选好物",
                    return_screen=self.return_screen_name or "store_category",
                )
                return
            if self.screen_ref and hasattr(self.screen_ref, "open_product_detail"):
                self.screen_ref.open_product_detail(self.product_id)
        except Exception as exc:
            show_toast(f"打开商品失败: {exc}")


Factory.register("ProductRow", cls=ProductRow)


class StoreRecycleView(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_scroll_x = False
        self.bar_width = dp(4)
        self.scroll_type = ["bars", "content"]
        self._data = []
        self.content_box = BoxLayout(orientation="vertical", size_hint=(1, None), spacing=0)
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        self.add_widget(self.content_box)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, items):
        self._data = list(items or [])
        self.content_box.clear_widgets()
        for item in self._data:
            row = ProductRow(
                product_id=item.get("product_id", 0),
                name_text=item.get("name_text", ""),
                specification_text=item.get("specification_text", ""),
                price_text=item.get("price_text", ""),
                sold_text=item.get("sold_text", ""),
                screen_ref=item.get("screen_ref"),
            )
            self.content_box.add_widget(row)
        Clock.schedule_once(lambda dt: self._reset_scroll(), 0)

    def _reset_scroll(self):
        self.scroll_y = 1
