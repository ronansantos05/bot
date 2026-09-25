from pokebot.config import Config, Search
from pokebot.models import Product
from pokebot.stores.base import BlockedError
from pokebot.watcher import Watcher


class FakeStore:
    def __init__(self, products):
        self.products = products

    def search(self, query):
        if isinstance(self.products, Exception):
            raise self.products
        return self.products


class FakeNotifier:
    def __init__(self):
        self.sent = []

    def send(self, search, product, deal, old_price=None):
        self.sent.append((product.id, deal, old_price))


def make(tmp_path, products, **search_kw):
    search = Search(name="t", query="pokemon 30 anos", stores=["amazon"],
                    must_include=["pokemon", "30"], exclude=["capa"], **search_kw)
    cfg = Config(searches=[search], state_file=str(tmp_path / "state.json"))
    store = FakeStore(products)
    notifier = FakeNotifier()
    return Watcher(cfg, notifier=notifier, stores={"amazon": store}), store, notifier


def p(id, title="Pokémon 30 Anos Box", price=300.0):
    return Product("amazon", id, title, price, f"https://x/{id}")


def test_filters_and_dedup(tmp_path):
    w, store, n = make(tmp_path, [p("A"), p("B", "Capa Pokemon 30"), p("C", "Pokemon Scarlet")],
                       max_price=1000, target_price=350)
    assert w.run_once() == 1
    assert n.sent == [("A", True, None)]
    # Rodar de novo não repete o aviso.
    assert w.run_once() == 0


def test_price_limits(tmp_path):
    w, _, n = make(tmp_path, [p("A", price=2000), p("B", price=500)],
                   max_price=1000, target_price=350)
    w.run_once()
    assert n.sent == [("B", False, None)]


def test_price_drop_renotifies(tmp_path):
    w, store, n = make(tmp_path, [p("A", price=500)], target_price=350)
    w.run_once()
    store.products = [p("A", price=520)]
    w.run_once()
    store.products = [p("A", price=340)]
    w.run_once()
    assert n.sent == [("A", False, None), ("A", True, 500)]


def test_state_persists(tmp_path):
    w, _, _ = make(tmp_path, [p("A")])
    w.run_once()
    w2, _, n2 = make(tmp_path, [p("A")])
    assert w2.run_once() == 0 and n2.sent == []


def test_silent_first_run(tmp_path):
    w, store, n = make(tmp_path, [p("A"), p("D", price=100)], target_price=150)
    w.config.silent_first_run = True
    w.run_once()
    assert n.sent == [("D", True, None)]  # só o que já está no preço-alvo
    n.sent.clear()
    store.products = [p("A"), p("B")]
    w.run_once()
    assert n.sent == [("B", False, None)]


def test_blocked_store_backs_off(tmp_path):
    w, store, n = make(tmp_path, BlockedError("captcha"))
    assert w.run_once() == 0
    assert w.blocked_until["amazon"] > 0
    store.products = [p("A")]
    assert w.run_once() == 0  # ainda em pausa
