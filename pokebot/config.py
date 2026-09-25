from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SUPPORTED_STORES = ("amazon", "mercadolivre")


def normalize(text: str) -> str:
    """Minúsculas e sem acentos, para comparar "Pokémon" com "pokemon"."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


@dataclass
class Search:
    name: str
    query: str
    stores: list[str] = field(default_factory=lambda: list(SUPPORTED_STORES))
    must_include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    # Acima disso o anúncio é ignorado (evita cambista / preço absurdo).
    max_price: float | None = None
    # Igual ou abaixo disso: alerta URGENTE de "compre agora".
    target_price: float | None = None
    min_price: float | None = None

    def matches(self, title: str, price: float | None) -> bool:
        t = normalize(title)
        if any(normalize(w) not in t for w in self.must_include):
            return False
        if any(normalize(w) in t for w in self.exclude):
            return False
        if price is not None:
            if self.max_price is not None and price > self.max_price:
                return False
            if self.min_price is not None and price < self.min_price:
                return False
        return True

    def is_deal(self, price: float | None) -> bool:
        return price is not None and self.target_price is not None and price <= self.target_price


@dataclass
class Config:
    searches: list[Search]
    interval_seconds: int = 120
    state_file: str = "state.json"
    # Na primeira execução, só registra o que já existe sem notificar.
    silent_first_run: bool = False


def load_config(path: str | Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    searches = []
    for raw in data.get("searches", []):
        s = Search(**raw)
        unknown = set(s.stores) - set(SUPPORTED_STORES)
        if unknown:
            raise ValueError(f"Loja(s) desconhecida(s) em '{s.name}': {sorted(unknown)}")
        searches.append(s)
    if not searches:
        raise ValueError("Nenhuma busca configurada em 'searches'.")
    return Config(
        searches=searches,
        interval_seconds=int(data.get("interval_seconds", 120)),
        state_file=os.getenv("POKEBOT_STATE_FILE") or data.get("state_file", "state.json"),
        silent_first_run=bool(data.get("silent_first_run", False)),
    )
