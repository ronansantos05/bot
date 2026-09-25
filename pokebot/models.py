from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    store: str
    id: str
    title: str
    price: float | None
    url: str
    buy_url: str | None = None

    @property
    def key(self) -> str:
        return f"{self.store}:{self.id}"


def parse_brl(text: str | None) -> float | None:
    """Converte "R$ 1.234,56" / "1.234" / "1234.56" em float."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text)
    if not cleaned:
        return None
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif cleaned.count(".") >= 1 and len(cleaned.rsplit(".", 1)[1]) == 3:
        # "1.234" no formato brasileiro = milhar, não decimal
        cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def format_brl(value: float | None) -> str:
    if value is None:
        return "preço indisponível"
    s = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"
