from __future__ import annotations

import logging
import os

import requests

from .config import Search
from .models import Product, format_brl

log = logging.getLogger(__name__)

STORE_LABEL = {"amazon": "Amazon", "mercadolivre": "Mercado Livre"}


def build_message(search: Search, product: Product, deal: bool, old_price: float | None = None):
    store = STORE_LABEL.get(product.store, product.store)
    head = "🔥 NO SEU PREÇO — COMPRE JÁ" if deal else "🆕 Encontrado"
    title = f"{head}: {search.name} ({store})"
    price = format_brl(product.price)
    if old_price is not None and product.price is not None:
        price += f" (antes {format_brl(old_price)})"
    body = f"{product.title}\n{price}\n{product.url}"
    return title, body


class Notifier:
    """Envia para ntfy.sh e/ou Telegram, conforme as variáveis de ambiente."""

    def __init__(self):
        self.ntfy_topic = os.getenv("NTFY_TOPIC")
        self.ntfy_server = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
        self.tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.tg_chat = os.getenv("TELEGRAM_CHAT_ID")
        if not (self.ntfy_topic or (self.tg_token and self.tg_chat)):
            log.warning("Nenhum canal configurado (NTFY_TOPIC ou TELEGRAM_*): só vou logar.")

    def send(self, search: Search, product: Product, deal: bool, old_price: float | None = None):
        title, body = build_message(search, product, deal, old_price)
        log.info("ALERTA %s | %s", title, body.replace("\n", " | "))
        if self.ntfy_topic:
            self._ntfy(title, body, product, deal)
        if self.tg_token and self.tg_chat:
            self._telegram(title, body, product)

    def _ntfy(self, title: str, body: str, product: Product, deal: bool):
        actions = [{"action": "view", "label": "Abrir", "url": product.url}]
        if product.buy_url and product.buy_url != product.url:
            actions.append({"action": "view", "label": "Comprar", "url": product.buy_url})
        try:
            requests.post(
                self.ntfy_server,
                json={
                    "topic": self.ntfy_topic,
                    "title": title,
                    "message": body,
                    "priority": 5 if deal else 4,  # 5 = urgente
                    "tags": ["rotating_light"] if deal else ["eyes"],
                    "click": product.buy_url or product.url,
                    "actions": actions,
                },
                timeout=15,
            ).raise_for_status()
        except requests.RequestException as e:
            log.error("Falha ao enviar ntfy: %s", e)

    def _telegram(self, title: str, body: str, product: Product):
        buttons = [[{"text": "Abrir anúncio", "url": product.url}]]
        if product.buy_url and product.buy_url != product.url:
            buttons[0].append({"text": "🛒 Comprar", "url": product.buy_url})
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.tg_token}/sendMessage",
                json={
                    "chat_id": self.tg_chat,
                    "text": f"{title}\n\n{body}",
                    "disable_web_page_preview": False,
                    "reply_markup": {"inline_keyboard": buttons},
                },
                timeout=15,
            ).raise_for_status()
        except requests.RequestException as e:
            log.error("Falha ao enviar Telegram: %s", e)
