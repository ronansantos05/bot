from __future__ import annotations

import logging
import os
import re
from urllib.parse import quote

from bs4 import BeautifulSoup

from ..models import Product, parse_brl
from .base import BlockedError, make_session

API = "https://api.mercadolibre.com/sites/MLB/search"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
LIST = "https://lista.mercadolivre.com.br"
log = logging.getLogger(__name__)
ID_RE = re.compile(r"(MLB)-?(\d+)", re.I)


class MercadoLivreStore:
    """Usa a API oficial se houver credenciais; senão, lê a página de busca.

    Credenciais (em ordem de preferência):
    - ML_CLIENT_ID + ML_CLIENT_SECRET: o bot gera o token sozinho (não expira pra você).
    - ML_ACCESS_TOKEN: token pronto (expira em 6h).
    """

    name = "mercadolivre"

    def __init__(self, session=None, timeout: float = 20, access_token: str | None = None):
        self.session = session or make_session()
        self.timeout = timeout
        self.access_token = access_token or os.getenv("ML_ACCESS_TOKEN")
        self.client_id = os.getenv("ML_CLIENT_ID")
        self.client_secret = os.getenv("ML_CLIENT_SECRET")

    def search(self, query: str) -> list[Product]:
        if self.client_id and self.client_secret and not self.access_token:
            self.access_token = self._client_credentials_token()
        if self.access_token:
            return self._search_api(query)
        return self._search_html(query)

    def _client_credentials_token(self) -> str:
        resp = self.session.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        if not resp.ok:
            raise RuntimeError(f"ML recusou as credenciais ({resp.status_code}): {resp.text[:300]}")
        return resp.json()["access_token"]

    def _search_api(self, query: str) -> list[Product]:
        resp = self.session.get(
            API,
            params={"q": query, "sort": "price_asc", "limit": 50},
            headers={"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"},
            timeout=self.timeout,
        )
        if resp.status_code == 401 and self.client_id:
            self.access_token = None  # token venceu: gera outro na próxima busca
        if not resp.ok:
            raise RuntimeError(f"API do ML respondeu {resp.status_code}: {resp.text[:300]}")
        return parse_api_json(resp.json())

    def _search_html(self, query: str) -> list[Product]:
        slug = quote(re.sub(r"\s+", "-", query.strip()))
        resp = self.session.get(f"{LIST}/{slug}_NoIndex_True", timeout=self.timeout)
        if resp.status_code in (403, 429):
            raise BlockedError(f"Mercado Livre respondeu {resp.status_code}")
        if "account-verification" in resp.url or "suspicious-traffic" in resp.text[:2000]:
            raise BlockedError("Mercado Livre pediu verificação (tráfego suspeito)")
        resp.raise_for_status()
        products = parse_search_html(resp.text)
        if not products:
            title = BeautifulSoup(resp.text, "html.parser").title
            log.warning("ML sem resultados: status=%s url=%s título=%r tamanho=%d trecho=%r",
                        resp.status_code, resp.url, title.get_text(strip=True) if title else None,
                        len(resp.text), resp.text[:300])
        return products


def parse_api_json(data: dict) -> list[Product]:
    return [
        Product(
            store="mercadolivre",
            id=item["id"],
            title=item["title"],
            price=item.get("price"),
            url=item["permalink"],
            buy_url=item["permalink"],
        )
        for item in data.get("results", [])
    ]


def _card_price(card) -> float | None:
    # Preço atual; ignora o preço riscado ("de R$ X") que vem num <s>.
    for amount in card.select(".andes-money-amount"):
        if amount.find_parent("s") or "previous" in " ".join(amount.get("class", [])):
            continue
        frac = amount.select_one(".andes-money-amount__fraction")
        if not frac:
            continue
        cents = amount.select_one(".andes-money-amount__cents")
        text = frac.get_text(strip=True) + ("," + cents.get_text(strip=True) if cents else "")
        return parse_brl(text)
    return None


def parse_search_html(html: str) -> list[Product]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("li.ui-search-layout__item") or soup.select("div.poly-card")
    products, seen = [], set()
    for card in cards:
        link = (
            card.select_one("a.poly-component__title")
            or card.select_one("h2 a")
            or card.select_one("a.ui-search-link")
        )
        if not link or not link.get("href"):
            continue
        url = link["href"].split("#")[0]
        m = ID_RE.search(url)
        item_id = f"MLB{m.group(2)}" if m else url.split("?")[0]
        if item_id in seen:
            continue
        seen.add(item_id)
        products.append(
            Product(
                store="mercadolivre",
                id=item_id,
                title=link.get_text(" ", strip=True),
                price=_card_price(card),
                url=url,
                buy_url=url,
            )
        )
    return products


__all__ = ["MercadoLivreStore", "BlockedError", "parse_search_html", "parse_api_json"]
