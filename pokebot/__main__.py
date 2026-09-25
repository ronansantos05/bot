from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from .config import load_config
from .notify import Notifier
from .watcher import Watcher


def load_dotenv(path: str = ".env"):
    """Carrega KEY=valor de um .env sem sobrescrever variáveis já definidas."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)


def main():
    ap = argparse.ArgumentParser(prog="pokebot", description=__doc__)
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("--once", action="store_true", help="roda uma verificação e sai")
    ap.add_argument("--test-notify", action="store_true",
                    help="envia uma notificação de teste e sai")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    load_dotenv()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    config = load_config(args.config)

    if args.test_notify:
        from .models import Product
        search = config.searches[0]
        Notifier().send(search, Product("amazon", "TESTE", "Se você recebeu isto, o pokebot está funcionando.",
                                        search.target_price, "https://www.amazon.com.br"),
                        deal=True, head="✅ TESTE")
        return

    watcher = Watcher(config)
    if args.once:
        watcher.run_once()
    else:
        watcher.run_forever()


if __name__ == "__main__":
    main()
