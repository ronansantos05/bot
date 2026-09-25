from pathlib import Path

from pokebot.models import format_brl, parse_brl
from pokebot.stores import amazon, mercadolivre

FIX = Path(__file__).parent / "fixtures"


def test_parse_brl():
    assert parse_brl("R$ 1.234,56") == 1234.56
    assert parse_brl("349,90") == 349.90
    assert parse_brl("1.099") == 1099
    assert parse_brl("289") == 289
    assert parse_brl("12.5") == 12.5
    assert parse_brl("") is None
    assert parse_brl("grátis") is None


def test_format_brl():
    assert format_brl(1234.5) == "R$ 1.234,50"
    assert format_brl(None) == "preço indisponível"


def test_amazon_parser():
    items = amazon.parse_search_html((FIX / "amazon_search.html").read_text())
    assert [p.id for p in items] == ["B0POKE3001", "B0CAPA0001", "B0SEMPRECO"]
    first = items[0]
    assert first.title == "Pokémon TCG: Coleção Especial 30 Anos Pikachu"
    assert first.price == 349.90  # ignora o preço riscado
    assert first.url == "https://www.amazon.com.br/dp/B0POKE3001"
    assert "ASIN.1=B0POKE3001" in first.buy_url
    assert items[2].price is None


def test_ml_html_parser():
    items = mercadolivre.parse_search_html((FIX / "ml_search.html").read_text())
    assert [p.id for p in items] == ["MLB123456789", "MLB987654"]
    assert items[0].price == 1099.90  # ignora o "de R$ 1.299"
    assert items[0].url.endswith("_JM")
    assert items[1].price == 289
    assert items[1].title == "Pokémon 30th Anniversary Booster"


def test_ml_api_parser():
    data = {"results": [{"id": "MLB1", "title": "Pokemon 30", "price": 99.9,
                         "permalink": "https://ml/MLB1"}]}
    (p,) = mercadolivre.parse_api_json(data)
    assert (p.id, p.price, p.url) == ("MLB1", 99.9, "https://ml/MLB1")


class FakeResp:
    def __init__(self, status=200, url="https://lista.mercadolivre.com.br/x", text="", data=None):
        self.status_code, self.url, self.text, self._data = status, url, text, data
        self.ok = status < 400

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kw):
        self.calls.append(("GET", url, kw))
        return self.responses.pop(0)

    def post(self, url, **kw):
        self.calls.append(("POST", url, kw))
        return self.responses.pop(0)


def test_ml_verification_page_is_blocked(monkeypatch):
    import pytest
    from pokebot.stores.base import BlockedError
    for var in ("ML_ACCESS_TOKEN", "ML_CLIENT_ID", "ML_CLIENT_SECRET"):
        monkeypatch.delenv(var, raising=False)
    s = FakeSession(FakeResp(url="https://www.mercadolivre.com.br/gz/account-verification?go=x"))
    with pytest.raises(BlockedError):
        mercadolivre.MercadoLivreStore(session=s).search("pokemon")


def test_ml_client_credentials(monkeypatch):
    monkeypatch.delenv("ML_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("ML_CLIENT_ID", "id")
    monkeypatch.setenv("ML_CLIENT_SECRET", "secret")
    api = {"results": [{"id": "MLB1", "title": "Pokemon 30", "price": 10, "permalink": "u"}]}
    s = FakeSession(FakeResp(data={"access_token": "TOK"}), FakeResp(data=api))
    items = mercadolivre.MercadoLivreStore(session=s).search("pokemon")
    assert [p.id for p in items] == ["MLB1"]
    assert s.calls[0][2]["data"]["grant_type"] == "client_credentials"
    assert s.calls[1][2]["headers"]["Authorization"] == "Bearer TOK"
