# TechStore Support

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat-square&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Next.js](https://img.shields.io/badge/Next.js-000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)

**Idioma:** [English](README.md) | Português

Suporte ao cliente da **TechStore**, uma varejista fictícia de eletrônicos no Brasil. Um **supervisor** LangGraph encaminha cada ticket para agentes de billing, logística ou conta. Esses agentes consultam **fatos de pedido no PostgreSQL**, recuperam **documentos de política via RAG** e aplicam **regras determinísticas** antes de qualquer reembolso ou cancelamento. O LLM não inventa o estado do pedido.

O produto é o **TechStore Support**: um Portal do Cliente para o comprador e um Console de Suporte para o agente humano.

[Visão geral](#visão-geral) · [Funcionalidades](#funcionalidades) · [Arquitetura](#arquitetura) · [Capturas de tela](#capturas-de-tela) · [Como começar](#como-começar) · [Cenários de demo](#cenários-de-demo) · [API](#api) · [Estrutura do projeto](#estrutura-do-projeto) · [Testes](#testes) · [Deploy](#deploy)

![Chat ao vivo — assistente respondendo quando o pedido chega](Images/order-interaction-0.png)

## Visão geral

Isto não é um chatbot de FAQ. O TechStore Support responde a partir de três fontes de verdade:

- **PostgreSQL** guarda clientes, pedidos, pagamentos, envios e tickets — fatos, nunca inventados pelo modelo.
- **Motor de política** (`app/policies/`, `data/company/company.yaml`) avalia janelas de reembolso, limites de aprovação e regras de envio em Python antes de o modelo agir.
- **RAG (pgvector)** indexa procedimentos e FAQs em `data/knowledge_base/` — documentos que explicam a política, não linhas operacionais.

As ferramentas ficam no escopo do cliente autenticado. Números críticos (prazo de devolução, limites em BRL) vivem em `company.yaml` e nunca ficam só a cargo do LLM.

A UI Next.js fala com o FastAPI por um BFF, para que as chaves de API nunca cheguem ao navegador.

## Funcionalidades

- **Orquestração multiagente** — o supervisor LangGraph delega para workers de billing, logística e conta.
- **Três fontes de conhecimento** — banco operacional, políticas determinísticas e RAG sobre documentos estáticos.
- **Ferramentas no escopo do cliente** — `get_order`, `get_payments`, `get_shipment`, `check_refund_eligibility` e outras, vinculadas ao cliente do ticket.
- **Chat ao vivo** — streaming SSE de tokens, fan-out Redis pub/sub, `ticket_messages` persistidos.
- **Humano no loop** — a escalation pausa a automação; um humano assume no inbox do console.
- **Guardrails** — tentativas de jailbreak e prompt injection são recusadas; reembolsos fora da política não são executados.
- **Mundo sintético TechStore** — dados de demo reproduzíveis com anomalias rotuladas (`SCN-*`) para evals.
- **Observabilidade** — traces OpenTelemetry, Langfuse para LLM/tools, e um console de analytics (latência, taxa de escalation, tool calls).

## Arquitetura

```mermaid
flowchart TD
    Browser[Next.js BFF + UI] --> API[FastAPI Routes]
    API --> Guard[Guardrails]
    Guard --> Graph[LangGraph Workflow]
    Graph --> Supervisor[Supervisor]
    Supervisor --> Billing[Billing Agent]
    Supervisor --> Logistics[Logistics Agent]
    Supervisor --> Account[Account Agent]
    Supervisor --> Escalation[Escalation Agent]
    Billing --> Tools[Scoped Tools]
    Billing --> RAG[pgvector RAG]
    Billing --> Policy[Policy Engine]
    Logistics --> Tools
    Account --> Tools
    Tools --> DB[(PostgreSQL facts)]
    RAG --> KB[Policy documents]
    Policy --> YAML[company.yaml]
    API --> Redis[(Redis cache + pub/sub)]
```

| Camada | Tecnologia |
|--------|------------|
| API | FastAPI, Pydantic, Uvicorn |
| Agentes | LangGraph (supervisor + workers de domínio) |
| LLM | Compatível com OpenAI (configurado via env) |
| RAG | PostgreSQL + pgvector |
| Cache / eventos ao vivo | Redis (Valkey na nuvem) |
| Observabilidade | OpenTelemetry, Langfuse |
| Frontend | Next.js 16 (Portal do Cliente + Console de Suporte) |
| Infraestrutura | Docker, Docker Compose, GitHub Actions |

## Capturas de tela

### Portal do Cliente

Login só por e-mail. Endereços desconhecidos são recusados; o portal nunca cria clientes.

![Login do portal do cliente](Images/interface-portal-customer.png)

Depois do login, o TechStore Support reconhece os pedidos do cliente e abre o chat ao vivo na mesma tela.

![Início do cliente com pedidos](Images/portal-customer-orders.png)

Perguntas rotineiras — previsão de entrega, status de pagamento, itens — são respondidas a partir do PostgreSQL, não da memória do modelo.

Quando a automação não consegue resolver o caso (divergência de pagamento, exceção, checagem de identidade), o ticket escala e um humano continua no mesmo fio.

![Escalation e resposta humana no portal](Images/order-interaction-4-human-intervection.png)

### Console de Suporte

Console em tema escuro para a equipe: inbox ao vivo, takeover, tickets e analytics.

![Inbox do console de suporte](Images/interface-portal-console-suport.png)

Num ticket escalado, o agente vê a transcrição, o resumo do pedido e a trilha de tools que o assistente já executou — e assume com **Assumir conversa**.

![Takeover humano com contexto do pedido e trilha de tools](Images/chat-console-suport.png)

### Analytics

Telemetria do agente: volume de tickets, taxa de escalation, confiança média, latência de execução, mix de intents e, por tool, taxa de erro / latência p95.

![Analytics — taxa de escalation, latência e tool calls](Images/analytics.png)

### Segurança

Tentativas de jailbreak e prompt injection são ignoradas. O assistente permanece na política da TechStore e escala em vez de executar reembolsos não autorizados.

![Tentativa de jailbreak recusada; caso encaminhado a um humano](Images/jailbreak-simulation.png)

## Como começar

### Pré-requisitos

- Python 3.12 (gerenciado via [uv](https://docs.astral.sh/uv/))
- Node.js 20+ (para a UI Next.js)
- Docker e Docker Compose
- Chave de API OpenAI

### Setup do backend

```bash
# Copiar o arquivo de ambiente
cp .env.example .env
# Editar .env — definir OPENAI_API_KEY

# Bootstrap (Windows) — define UV_LINK_MODE=copy para evitar erros de hardlink
./scripts/bootstrap.ps1

# Ou manualmente (Windows: sempre use copy link mode)
export UV_LINK_MODE=copy          # bash
# $env:UV_LINK_MODE = "copy"      # PowerShell
uv sync --link-mode=copy
docker compose up -d db redis
uv run alembic upgrade head
uv run python scripts/generate_data.py --profile demo --seed 42
uv run python scripts/ingest_kb.py
uv run fastapi dev
```

### Setup do frontend

```bash
cp web/.env.example web/.env.local
cd web
npm install
npm run dev
```

| URL | Função |
|-----|--------|
| http://localhost:3000 | Portal do cliente |
| http://localhost:3000/portal/login | Login por e-mail |
| http://localhost:3000/login | Console de suporte (senha padrão `console`) |
| http://localhost:3000/console/inbox | Inbox ao vivo |
| http://localhost:8000/docs | Documentação OpenAPI |

> [!TIP]
> A UI faz proxy das chamadas de API por `/api/support/*`. `SUPPORT_API_KEY` e `X-Customer-Email` são injetados no servidor — nunca os exponha com `NEXT_PUBLIC_`.

> [!NOTE]
> **Database URL:** o desenvolvimento local usa PostgreSQL na porta do host **5433** (`localhost:5433`) para o Docker não conflitar com um Postgres local em 5432. Se 5433 estiver ocupada, ajuste `POSTGRES_HOST_PORT` e `DATABASE_URL` juntos. Veja `.env.example`.

### Notas para Windows

No Windows, o `uv` pode falhar com **os error 396** (*cloud operation incompatible with hardlinks*) quando o projeto, `.venv` ou o cache em `%LOCALAPPDATA%\uv` está em um caminho sincronizado na nuvem. O script de bootstrap define `UV_LINK_MODE=copy` e usa `C:\uv-cache` por padrão quando `UV_CACHE_DIR` não está definido.

Se o problema persistir:

- Prefira um caminho local como `C:\dev\seu-projeto` (fora do OneDrive).
- Ou defina `UV_PROJECT_ENVIRONMENT=C:\venvs\seu-projeto` para o `.venv` não ficar numa pasta sincronizada.
- Reconstrua: `Remove-Item -Recurse -Force .venv` e depois `uv sync --link-mode=copy`.

## Cenários de demo

Depois de `generate_data.py --profile demo --seed 42`, entre em `/portal/login`:

| E-mail | Nome | Cenário típico |
|--------|------|----------------|
| `demo@test.com.br` | Demo Tester | **10 pedidos** — roteiro manual em [`data/fixtures/demo_manual_tests.md`](data/fixtures/demo_manual_tests.md) |
| `ana.costa@nexamail.com` | Ana Costa | Cobrança duplicada (`SCN-DOUBLE-PAY-001`) |
| `pedro.lima@outlook.com` | Pedro Lima | Envio atrasado |
| `rafaela.fernandes@uol.com.br` | Rafaela Fernandes | Entregue, mas ausente |
| `nicolas.dias@outlook.com` | Nicolas Dias | Reembolso de alto valor |

Lista completa de logins: [`data/fixtures/demo_logins.json`](data/fixtures/demo_logins.json).

O cliente de demo (`demo@test.com.br`) cobre dez cenários rotulados — pagamento duplicado, envio atrasado, reembolso fora da janela, reembolso de alto valor e outros. Cada linha em `demo_manual_tests.md` lista o ID do pedido, a mensagem sugerida, as tools esperadas e se a escalation humana é esperada.

```bash
uv run python scripts/generate_data.py --profile demo --seed 42
uv run python scripts/generate_data.py --profile v1 --seed 42 --replace
```

| Perfil | Descrição |
|--------|-----------|
| `demo` | Smoke local — todos os tipos de anomalia |
| `v1` | 1000 clientes / 3000 pedidos |
| `load` | Escala opcional para teste de carga |

Os fixtures são gravados em `data/fixtures/scenarios.json`. Não coloque linhas de pedido na base de conhecimento.

## API

Todos os endpoints exigem o header `X-API-Key` (padrão: `dev-key` em `.env.example`).

```bash
# Health check
curl http://localhost:8000/health

# Criar ticket
curl -X POST http://localhost:8000/tickets \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "customer@example.com",
    "customer_name": "Customer",
    "subject": "Refund request",
    "description": "I was charged twice for INV-1001"
  }'

# Resolver ticket (turno de chat)
curl -X POST http://localhost:8000/tickets/{ticket_id}/resolve \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Please refund duplicate charge on INV-1001"}]}'
```

O chat do portal usa `POST /tickets/{id}/messages` e `GET /tickets/{id}/events` (SSE).

## Estrutura do projeto

```
app/                  # Backend FastAPI + LangGraph
├── api/routes/       # tickets, portal, health
├── agents/           # supervisor, billing, logistics, account, escalation
├── graph/            # state, nodes, edges, workflow
├── tools/            # ferramentas de domínio no escopo do cliente
├── policies/         # motor de política determinístico
├── retrieval/        # embeddings, retriever pgvector
├── models/           # modelos SQLAlchemy
├── services/         # listagem de tickets, graph runner, chat_bus, analytics
└── evaluation/       # datasets, evaluators, metrics

web/                  # Portal do Cliente + Console de Suporte (Next.js)
data/
├── company/          # modelo de mundo company.yaml
├── fixtures/         # fixtures de eval SCN-*, logins de demo
└── knowledge_base/   # documentos RAG (políticas, procedimentos, FAQ)

scripts/              # generate_data, seed_demo, ingest_kb
tests/                # unit, integration, evaluation
Images/               # capturas de tela do README
```

## Testes

```bash
uv run pytest tests/unit -v
uv run pytest tests/integration -v
uv run pytest tests/evaluation -v
```

As suítes de unit + integration passam hoje em **160 testes**, com cerca de **70%** de cobertura. Os limiares de avaliação ficam em `app/evaluation/metrics.py` (acurácia de intent, correção de tool calls, conformidade de política, taxa de ação não autorizada = 0). Publique scores medidos só depois de uma execução real de eval.

## Deploy

O Docker Compose sobe o stack completo localmente (`db`, `redis`, `api`, `web`):

```bash
docker compose up -d
```

Um deploy próximo de produção na **DigitalOcean App Platform** separa as mesmas peças em serviços:

- **API** — FastAPI + LangGraph
- **Web** — Portal do Cliente e Console de Suporte (Next.js)
- **PostgreSQL** (pgvector) — fatos operacionais e embeddings
- **Valkey / Redis** — cache e pub/sub do chat
- **Jobs de seed / ingest** — dados sintéticos da TechStore e documentos da base de conhecimento

![DigitalOcean App Platform — API, web, PostgreSQL, Valkey e job de seed](Images/deploy-components.png)

## Troubleshooting

| Sintoma | Correção |
|---------|----------|
| Auth do Postgres falhou na porta 5432 | Use `localhost:5433` em `DATABASE_URL` (Docker mapeia `5433:5432`) |
| Auth do Postgres falhou na porta 5433 | Outro container ocupa 5433 — defina `POSTGRES_HOST_PORT` e `DATABASE_URL` para uma porta livre (ex.: 5434) |
| `ProactorEventLoop` no seed/ingest | Use os `scripts/` atuais — no Windows é preciso `SelectorEventLoop` |
| API falha com `CREATE INDEX CONCURRENTLY` | O pool do checkpointer precisa de `autocommit=True` em `app/graph/workflow.py` |
| Loop de reload do `fastapi dev` em `.venv` | Use `uv run fastapi run` ou pare o `uv sync` enquanto o servidor roda |
| Resposta do assistente só aparece depois de F5 | Confirme que o Redis está no ar e recarregue o portal |
| Bolhas de chat duplicadas | Recarregue a página; o último turno do assistente não deve se repetir |

## Variáveis de ambiente

Veja [.env.example](.env.example) e [`web/.env.example`](web/.env.example) para todas as opções. Variáveis principais:

| Variável | Função |
|----------|--------|
| `DATABASE_URL` | PostgreSQL + pgvector (`localhost:5433` no local) |
| `REDIS_URL` | Cache + pub/sub do chat |
| `OPENAI_API_KEY` | LLM + embeddings |
| `API_KEYS` | Chaves de API separadas por ponto e vírgula, com escopos |
| `LANGFUSE_*` | Tracing opcional |
| `SUPPORT_API_URL` / `SUPPORT_API_KEY` | BFF Next.js → FastAPI (somente servidor) |
| `CONSOLE_PASSWORD` | Login do console de suporte |
| `PORTAL_SESSION_SECRET` | HMAC do cookie de sessão do cliente |
