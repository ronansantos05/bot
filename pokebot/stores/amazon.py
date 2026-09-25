from __future__ import annotations

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from ..models import Product, parse_brl
from .base import BlockedError, make_session

BASE = "https://www.amazon.com.br"


class AmazonStore:
    name = "amazon"

    def __init__(self, session=None, timeout: float = 20):
        self.session = session or make_session()
        self.timeout = timeout

    def search(self, query: str) -> list[Product]:
        # s=date-desc-rank: mais recentes primeiro, para pegar lançamentos.
        url = f"{BASE}/s?k={quote_plus(query)}&s=date-desc-rank"
        resp = self.session.get(url, timeout=self.timeout)
        if resp.status_code == 503 or "validateCaptcha" in resp.text:
            raise BlockedError("Amazon pediu captcha")
        resp.raise_for_status()
        return parse_search_html(resp.text)


def cart_url(asin: str) -> str:
    """Link que abre a Amazon já com o item no carrinho (é só confirmar)."""
    return f"{BASE}/gp/aws/cart/add.html?ASIN.1={asin}&Quantity.1=1"


def parse_search_html(html: str) -> list[Product]:
    soup = BeautifulSoup(html, "html.parser")
    products = []
    for card in soup.select('div[data-component-type="s-search-result"][data-asin]'):
        asin = card.get("data-asin", "").strip()
        if not asin:
            continue
        title_el = card.select_one("h2 span") or card.select_one("h2")
        if not title_el:
            continue
        title = title_el.get_text(" ", strip=True)
        price_el = card.select_one(".a-price:not(.a-text-price) .a-offscreen")
        price = parse_brl(price_el.get_text()) if price_el else None
        products.append(
            Product(
                store="amazon",
                id=asin,
                title=title,
                price=price,
                url=f"{BASE}/dp/{asin}",
                buy_url=cart_url(asin),
            )
        )
    return products
