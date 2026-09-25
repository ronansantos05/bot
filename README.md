# pokebot — alerta de produtos Pokémon 30 anos

Bot que fica verificando a **Amazon.com.br** e o **Mercado Livre** atrás de produtos
Pokémon 30 anos e manda **push no celular na hora** (ntfy e/ou Telegram) quando
aparece um anúncio novo, quando o preço cai ou quando fica **igual ou abaixo do preço-alvo**.

## Como funciona

- A cada `interval_seconds` (padrão 120s, com variação aleatória), roda cada busca do `config.yaml`.
- Filtra pelo título (`must_include` / `exclude`, sem diferenciar acento nem maiúscula) e pela faixa de preço.
- Avisa **uma vez** por anúncio (fica registrado em `state.json`) e avisa de novo se o preço cair.
- Se o preço for `<= target_price`, o alerta sai como **URGENTE** ("🔥 NO SEU PREÇO — COMPRE JÁ").
- Na Amazon, o botão **Comprar** abre o site com o item **já no carrinho**: você só confirma.
- Se uma loja bloquear (captcha), o bot pausa só aquela loja (1 min, 2, 4… até 1h) e continua com a outra.

## Instalação

```bash
git clone <este repo> && cd bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml   # edite as buscas e os preços
cp .env.example .env                 # configure a notificação
```

### Notificação no celular (escolha uma ou as duas)

**ntfy (a mais simples, sem conta):**
1. Instale o app **ntfy** (Android/iOS).
2. Toque em "+", escolha um nome de tópico difícil de adivinhar (ex.: `pokebot-ronan-8f3k2`).
3. Coloque o mesmo nome em `NTFY_TOPIC` no `.env`.
4. No app, ative a prioridade máxima para o tópico, assim o alerta urgente toca alto.

**Telegram:**
1. Fale com o `@BotFather`, use `/newbot` e copie o token para `TELEGRAM_BOT_TOKEN`.
2. Mande qualquer mensagem pro seu bot e pegue seu id com o `@userinfobot`. Coloque em `TELEGRAM_CHAT_ID`.

Teste:

```bash
python -m pokebot --test-notify
```

## Rodando

```bash
python -m pokebot --once   # uma verificação só, para testar os filtros
python -m pokebot          # fica rodando para sempre
```

Dica: na primeira vez, use `silent_first_run: true` se não quiser receber aviso de tudo o
que já está à venda. A partir daí, você só recebe os anúncios **novos**.

### 24h por dia

O bot precisa ficar ligado em algum lugar. Opções:

- **Seu PC / Raspberry Pi** ligado direto.
- **VPS barata ou grátis** (Oracle Cloud Free Tier, por exemplo) com Docker:
  ```bash
  cp config.example.yaml config.yaml && cp .env.example .env   # edite os dois
  docker compose up -d --build
  docker compose logs -f
  ```

> IPs de datacenter são bloqueados pela Amazon com mais frequência que IP residencial.
> Se só a Amazon ficar dando captcha, rode o bot em casa (PC ou Raspberry Pi).

## Configuração (`config.yaml`)

| Campo | O que faz |
|---|---|
| `query` | Texto buscado na loja |
| `stores` | `[amazon, mercadolivre]` |
| `must_include` | O título precisa ter **todas** essas palavras |
| `exclude` | Descarta se o título tiver **qualquer** uma (capa, sleeve, camiseta…) |
| `max_price` | Ignora anúncios mais caros que isso (cambistas) |
| `min_price` | Ignora anúncios mais baratos que isso (acessórios, golpe) |
| `target_price` | Igual ou abaixo disso: alerta **urgente** de compra |

### Mercado Livre: API oficial (opcional)

Sem token, o bot lê a página de busca pública. Para ficar mais estável, crie um app em
<https://developers.mercadolivre.com.br>, gere um access token e coloque em `ML_ACCESS_TOKEN`.
O token expira em 6h, então isso só compensa se você for automatizar a renovação.

## E comprar sozinho?

**Não implementado de propósito.** Dá para fazer um robô de navegador (Playwright) que faz
login e finaliza a compra, mas:

- Os Termos de Uso da Amazon e do Mercado Livre **proíbem** automação desse tipo. Conta
  bloqueada é o risco real, e aí você perde a conta junto com os pedidos e o saldo.
- Você teria que deixar senha + cartão/2FA dentro do bot, e o checkout ainda pede captcha
  e confirmação no app do banco com frequência, então quebraria justo na hora do lançamento.
- Se um filtro falhar, o bot pode comprar a coisa errada (uma capa, um produto falso de
  vendedor novo…) sem você ver.

O que o bot faz no lugar disso: alerta **urgente** + botão **Comprar** que abre o item já no
carrinho (Amazon) ou direto no anúncio (Mercado Livre). Com o cartão salvo e a compra
em 1 clique ativada no app da loja, dá para fechar em poucos segundos.

## Limitações

- Scraping depende do HTML das lojas. Se mudarem o layout, o bot passa a logar
  "0 resultados" e o parser (`pokebot/stores/*.py`) precisa ser ajustado.
- Não verifica a reputação do vendedor no Mercado Livre. Confira antes de pagar.

## Testes

```bash
pip install pytest && python -m pytest
```
