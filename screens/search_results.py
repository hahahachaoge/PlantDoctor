from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout

from config import COMMUNITY_ARTICLES, COMMUNITY_POSTS, GREEN
from database.store_db import STORE_DB
from screens.account_pages import AccountPage, INK, MUTED, SOFT_GREEN, _text
from utils import show_toast, text_style
from widgets.base_widgets import RoundedButton


class SearchResultsScreen(AccountPage):
    title = "搜索结果"
    subtitle = ""

    def __init__(self, **kwargs):
        kwargs.setdefault("name", "search_results")
        super().__init__(**kwargs)
        self.keyword = ""
        self.results = []

    def go_back(self, *_args):
        if self.manager:
            self.manager.current = "home"

    def show_results(self, keyword):
        self.keyword = (keyword or "").strip()
        self.results = self._search(self.keyword)
        self._render()

    def on_pre_enter(self, *_args):
        self._render()

    @staticmethod
    def _matches(keyword, *values):
        haystack = " ".join(str(value or "") for value in values).casefold()
        return keyword.casefold() in haystack

    def _search(self, keyword):
        if not keyword:
            return []
        results = []
        for pest in STORE_DB.get_pest_entries():
            if self._matches(
                    keyword, pest.get("name"), pest.get("intro"),
                    pest.get("treatment"), pest.get("crop"), pest.get("en_name")):
                results.append({
                    "kind": "病虫害", "title": pest["name"],
                    "summary": (
                        f"{pest.get('crop')} · {pest.get('intro')}"
                        if pest.get("crop") else pest.get("intro") or "暂无简介"),
                    "data": pest,
                })
        for pesticide in STORE_DB.get_pesticide_entries():
            if self._matches(
                    keyword, pesticide.get("name"), pesticide.get("type"),
                    pesticide.get("crops"), pesticide.get("target"),
                    pesticide.get("method"), pesticide.get("caution")):
                results.append({
                    "kind": "农药百科", "title": pesticide["name"],
                    "summary": (
                        f"{pesticide.get('type', '农药')} · "
                        f"防治对象：{pesticide.get('target', '暂无')}"),
                    "data": pesticide,
                })
        for product in STORE_DB.search_products(keyword):
            results.append({
                "kind": "商城商品", "title": product["name"],
                "summary": (
                    f"{product.get('specification', '')} · "
                    f"¥{float(product.get('price', 0)):.2f}"),
                "data": product,
            })
        community_items = list(COMMUNITY_POSTS) + list(COMMUNITY_ARTICLES.values())
        for item in community_items:
            if self._matches(
                    keyword, item.get("title"), item.get("summary"),
                    item.get("full_text"), item.get("username")):
                results.append({
                    "kind": "社区内容", "title": item["title"],
                    "summary": item.get("summary") or item.get("full_text", "")[:80],
                    "data": item,
                })

        folded = keyword.casefold()
        results.sort(key=lambda row: (
            0 if row["title"].casefold() == folded else
            1 if row["title"].casefold().startswith(folded) else
            2 if folded in row["title"].casefold() else 3,
            row["kind"], row["title"],
        ))
        return results

    def _render(self):
        self.body.clear_widgets()
        if not self.keyword:
            self.body.add_widget(_text(
                "请在首页输入关键词后搜索", 14, MUTED, 90, halign="center"))
            return
        summary = self.card(82, color=(0.84, 0.95, 0.87, 1))
        summary.add_widget(_text(f"关键词：{self.keyword}", 18, INK, 30, True))
        summary.add_widget(_text(
            f"找到 {len(self.results)} 条相关内容", 12, MUTED, 24))
        self.body.add_widget(summary)
        if not self.results:
            empty = self.card(180)
            empty.add_widget(_text("没有找到相关内容", 18, INK, 48, True, "center"))
            empty.add_widget(_text(
                "可以尝试作物名称、病虫害、农药名称或种植关键词。",
                13, MUTED, 64, halign="center"))
            self.body.add_widget(empty)
            return
        for index, result in enumerate(self.results, start=1):
            card = self.card(148, padding=12, spacing=4)
            top = BoxLayout(size_hint=(1, None), height=dp(28))
            top.add_widget(_text(f"{index}. {result['title']}", 15, INK, 28, True))
            top.add_widget(_text(
                result["kind"], 11, GREEN, 28, True, "right",
                size_hint=(None, None), width=dp(76)))
            card.add_widget(top)
            card.add_widget(_text(result["summary"], 12, MUTED, 62))
            button = RoundedButton(
                text="查看内容", size_hint=(1, None), height=dp(38),
                color=GREEN, fill_color=SOFT_GREEN, **text_style())
            button.bind(on_release=lambda *_args, row=result: self._open_result(row))
            card.add_widget(button)
            self.body.add_widget(card)
        self.scroll.scroll_y = 1

    def _open_result(self, result):
        kind = result["kind"]
        data = result["data"]
        if kind == "病虫害":
            page = self.manager.get_screen("pest_detail")
            page.return_screen = "search_results"
            page.set_pest(data["id"])
            self.manager.current = "pest_detail"
        elif kind == "农药百科":
            page = self.manager.get_screen("pesticide_detail")
            page.return_screen = "search_results"
            page.set_pesticide(data["id"])
            self.manager.current = "pesticide_detail"
        elif kind == "商城商品":
            App.get_running_app().open_product_detail_screen(
                data["id"], return_screen="search_results")
        elif kind == "社区内容":
            page = self.manager.get_screen("community_detail")
            page.set_item(data, return_screen="search_results")
            self.manager.current = "community_detail"
        else:
            show_toast("暂时无法打开该内容")
