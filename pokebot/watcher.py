from __future__ import annotations

import logging
import random
import time

from .config import Config, Search
from .notify import Notifier
from .state import State
from .stores import AmazonStore, MercadoLivreStore
from .stores.base import BlockedError

log = logging.getLogger(__name__)


class Watcher:
    def __init__(self, config: Config, notifier=None, stores=None):
        self.config = config
        self.notifier = notifier or Notifier()
        self.stores = stores or {"amazon": AmazonStore(), "mercadolivre": MercadoLivreStore()}
        self.state = State(config.state_file)
        self.blocked_until: dict[str, float] = {}
        self.block_count: dict[str, int] = {}

    def check_search(self, search: Search, silent: bool = False) -> int:
        sent = 0
        for store_name in search.stores:
            if time.time() < self.blocked_until.get(store_name, 0):
                continue
            store = self.stores[store_name]
            try:
                products = store.search(search.query)
                self.block_count[store_name] = 0
            except BlockedError as e:
                n = self.block_count.get(store_name, 0) + 1
                self.block_count[store_name] = n
                wait = min(60 * 2**n, 3600)
                self.blocked_until[store_name] = time.time() + wait
                log.warning("%s bloqueou (%s). Pausando essa loja por %ds.", store_name, e, wait)
                continue
            except Exception as e:  # rede, HTML mudou etc.: não derruba o bot
                log.error("Erro buscando '%s' em %s: %s", search.query, store_name, e)
                continue

            matched = [p for p in products if search.matches(p.title, p.price)]
            log.info("%s '%s': %d resultados, %d batem com o filtro",
                     store_name, search.query, len(products), len(matched))
            for p in matched:
                key = f"{search.name}|{p.key}"
                is_new = key not in self.state.seen
                old = self.state.seen.get(key)
                dropped = (not is_new and p.price is not None
                           and (old is None or p.price < old))
                if (is_new or dropped) and not silent:
                    self.notifier.send(search, p, search.is_deal(p.price),
                                       old_price=old if dropped else None)
                    sent += 1
                if is_new or dropped:
                    self.state.seen[key] = p.price
        return sent

    def run_once(self) -> int:
        silent = self.config.silent_first_run and self.state.empty
        if silent:
            log.info("Primeira execução: registrando anúncios existentes sem notificar.")
        sent = sum(self.check_search(s, silent=silent) for s in self.config.searches)
        self.state.save()
        return sent

    def run_forever(self):
        log.info("Monitorando %d busca(s) a cada ~%ds. Ctrl+C para parar.",
                 len(self.config.searches), self.config.interval_seconds)
        while True:
            self.run_once()
            # Variação aleatória para não parecer robô batendo no relógio.
            base = self.config.interval_seconds
            time.sleep(base + random.uniform(-0.2, 0.2) * base)
