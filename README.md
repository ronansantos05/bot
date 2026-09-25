# pokebot — alerta de produtos Pokémon 30 anos

Bot que fica verificando a **Amazon.com.br** e o **Mercado Livre** atrás de produtos
Pokémon 30 anos e manda **push no celular na hora** (ntfy e/ou Telegram) quando
aparece um anúncio novo, quando o preço cai ou quando fica **igual ou abaixo do preço-alvo**.

## Como funciona

- Roda cada busca do `config.yaml`: no GitHub a cada ~5 min; no PC a cada `interval_seconds` (padrão 120s).
- Filtra pelo título (`must_include` / `exclude`, sem diferenciar acento nem maiúscula) e pela faixa de preço.
- Avisa **uma vez** por anúncio (fica registrado em `state.json`) e avisa de novo se o preço cair.
- Se o preço for `<= target_price`, o alerta sai como **URGENTE** ("🔥 NO SEU PREÇO — COMPRE JÁ").
- Na Amazon, o botão **Comprar** abre o site com o item **já no carrinho**: você só confirma.
- Se uma loja bloquear (captcha), o bot pausa só aquela loja (1 min, 2, 4… até 1h) e continua com a outra.

## Rodando no GitHub (sem precisar do seu PC)

O bot roda sozinho pelo **GitHub Actions** (`.github/workflows/pokebot.yml`), a cada ~5 minutos.
Esse repositório é público, então os minutos são de graça. Só falta uma coisa que você precisa
fazer, porque o nome do tópico do ntfy é secreto e não pode ficar no código:

1. No app **ntfy**, toque em **+** e assine um tópico com um nome difícil de adivinhar
   (ex.: `pokebot-ronan-x7k29q`). Qualquer um que souber o nome recebe os seus avisos.
2. No GitHub, abra o repositório e vá em **Settings → Secrets and variables → Actions →
   New repository secret**. Em *Name* coloque `NTFY_TOPIC` e em *Secret* o nome do tópico.
3. Vá em **Actions → pokebot → Run workflow**. Na primeira vez chega uma notificação
   **"✅ TESTE"** no celular. Se chegou, está pronto: a partir daí ele roda sozinho.

Para mudar buscas ou preços, edite o `config.yaml` direto no GitHub (ícone de lápis) e salve.
A próxima rodada já usa a versão nova.

Na primeira rodada, o bot só avisa o que **já está no preço-alvo**. O resto ele só registra, para
não mandar dezenas de avisos de uma vez. Depois disso, avisa todo anúncio **novo**.

### Limites de rodar no GitHub (testado)

As duas lojas **bloqueiam os servidores do GitHub** quando o bot lê o site direto:
- **Amazon:** responde com captcha. Pelo GitHub a Amazon **não funciona**.
- **Mercado Livre:** redireciona para "verificação de conta / tráfego suspeito". A saída é usar a
  **API oficial**, que aceita servidor. Veja "Mercado Livre pelo GitHub" abaixo.

Outros limites:
- **Não é instantâneo:** o intervalo mínimo é 5 min, e o GitHub atrasa em horário de pico.
- Em repositório público, o GitHub **pausa agendamentos depois de 60 dias sem commit**
  (ele manda e-mail antes). É só reativar em Actions.
- Os termos do GitHub Actions pedem uso ligado a projetos de software. Um bot pequeno de 5 em 5 min
  é tolerado na prática, mas não é garantido.

Para a Amazon, o jeito que funciona é rodar em casa (PC ligado, notebook velho ou Raspberry Pi),
porque a internet residencial quase não é bloqueada.

### Mercado Livre pelo GitHub (API oficial)

1. Entre em <https://developers.mercadolivre.com.br> com sua conta do ML e vá em
   **Minhas aplicações → Criar aplicação**.
2. Preencha nome e descrição. Em *URI de redirect* pode colocar `https://github.com/ronansantos05/bot`.
   Nas permissões, só leitura já basta.
3. Copie o **Client ID** (ou "App ID") e a **Client Secret** (ou "Chave secreta").
4. No GitHub, crie os secrets `ML_CLIENT_ID` e `ML_CLIENT_SECRET`, do mesmo jeito que o `NTFY_TOPIC`.

O bot gera o token sozinho a cada rodada, então você não precisa renovar nada.

## Rodando no seu PC / VPS (verificação mais rápida)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # coloque NTFY_TOPIC
python -m pokebot --test-notify      # testa a notificação
python -m pokebot --once             # uma verificação só
python -m pokebot                    # fica rodando (a cada interval_seconds)
```

Ou com Docker (VPS, Raspberry Pi): `cp .env.example .env`, edite, e `docker compose up -d --build`.

### Telegram (opcional)

Crie um bot com o `@BotFather` (`/newbot`) e pegue seu id com o `@userinfobot`. Coloque em
`TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`, como secrets no GitHub ou no `.env`.

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
