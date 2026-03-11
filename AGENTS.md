# AGENTS.md — Crypto Network Intelligence API

## Project Overview

This is a **crypto network intelligence API** designed **AI-first** with a native MCP (Model Context Protocol) layer. Its core purpose is to help AI agents decide **which blockchain network to use** for a given transaction based on real-time scoring of safety, reliability, cost, and speed.

This is NOT a price/market data API. It is a **decision-making layer** on top of raw blockchain data.

---

## Core Problem Solved

> "Given that I need to send $500 USDC right now — which network should I use, how much will it cost exactly, and is it safe to do so?"

No existing tool answers this. This API does.

---

## Architecture

```
AI Agents (Claude, GPT, Gemini)
        │
        │ MCP Protocol (native)
        ▼
MCP Server Layer          ← /src/mcp/
        │
        │ Internal calls
        ▼
API Core (FastAPI)        ← /src/api/
        │
  ┌─────┼──────┐
  ▼     ▼      ▼
Scoring  Cache  Ingestion
Engine  (Redis) Layer
/src/   /src/   /src/
scoring/ cache/ ingestion/
        │
        ▼
External Data Sources
(CoinGecko, DefiLlama, public RPCs, GasNow, L2Beat)
```

---

## Project Structure

```
crypto-network-api/
├── AGENTS.md                  ← You are here
├── docker-compose.yml         ← Full local stack
├── pyproject.toml             ← Python deps (uv)
├── .env.example               ← Required env vars
│
├── crypto_core/ — módulo privado con lógica propietaria, no incluido en repo público
│
├── src/
│   ├── main.py                ← FastAPI entrypoint
│   │
│   ├── api/                   ← HTTP layer
│   │   ├── routes/
│   │   │   ├── networks.py    ← /v1/networks/*
│   │   │   ├── gas.py         ← /v1/gas/*
│   │   │   ├── transactions.py← /v1/transactions/*
│   │   │   └── alerts.py      ← /v1/alerts/*
│   │   ├── middleware/
│   │   │   ├── auth.py        ← API key validation
│   │   │   └── rate_limit.py  ← Per-tier rate limiting
│   │   └── deps.py            ← FastAPI dependencies
│   │
│   ├── mcp/                   ← MCP Server (AI-first layer)
│   │   ├── server.py          ← MCP server entrypoint
│   │   ├── tools/
│   │   │   ├── get_best_network.py
│   │   │   ├── compare_networks.py
│   │   │   ├── estimate_cost.py
│   │   │   ├── simulate_transaction.py
│   │   │   └── get_alerts.py
│   │   ├── resources/
│   │   │   ├── scores.py      ← crypto://networks/scores
│   │   │   ├── gas.py         ← crypto://gas/current
│   │   │   └── alerts.py      ← crypto://alerts/active
│   │   └── prompts/
│   │       └── transaction_advisor.py
│   │
│   ├── scoring/               ← The core differentiator
│   │   ├── engine.py          ← Main scoring orchestrator
│   │   ├── dimensions/
│   │   │   ├── safety.py      ← TVL, audits, hack history (35%)
│   │   │   ├── reliability.py ← Uptime, finality, reorgs (30%)
│   │   │   ├── cost.py        ← Gas fees, p90, 7d avg (25%)
│   │   │   └── speed.py       ← TPS, confirmation time (10%)
│   │   └── weights.py         ← Configurable score weights
│   │
│   ├── ingestion/             ← Data pipeline
│   │   ├── providers/
│   │   │   ├── coingecko.py
│   │   │   ├── defillama.py
│   │   │   ├── l2beat.py
│   │   │   ├── rpc_nodes.py   ← Direct RPC calls
│   │   │   └── gasnow.py
│   │   ├── normalizer.py      ← Unified data schema
│   │   └── scheduler.py       ← Celery task schedules
│   │
│   ├── models/
│   │   ├── network.py         ← Network Pydantic models
│   │   ├── score.py           ← Score models
│   │   ├── transaction.py     ← Transaction models
│   │   └── db/                ← SQLAlchemy models
│   │
│   ├── cache/
│   │   ├── redis.py           ← Redis client
│   │   └── ttl.py             ← TTL constants per data type
│   │
│   └── core/
│       ├── config.py          ← Settings (pydantic-settings)
│       ├── auth.py            ← API key management
│       └── logging.py         ← Structured logging
│
├── tests/
│   ├── unit/
│   │   ├── test_scoring.py
│   │   └── test_ingestion.py
│   └── integration/
│       ├── test_api.py
│       └── test_mcp.py
│
└── docs/
    ├── scoring-methodology.md ← How scores are calculated (public)
    └── mcp-tools.md           ← MCP tools reference
```

---

## Monitored Networks (Phase 1)

| ID | Network | Category | Why |
|----|---------|----------|-----|
| `solana` | Solana | L1 | Ultra-low cost, high TPS |
| `polygon` | Polygon PoS | L2/Sidechain | Mature, cheap, EVM-compatible |
| `arbitrum` | Arbitrum One | L2 Ethereum | Largest L2, secure, cheap |
| `base` | Base | L2 Ethereum | Coinbase-backed, growing fast |
| `optimism` | Optimism | L2 Ethereum | Mature, OP Stack ecosystem |
| `avalanche` | Avalanche C-Chain | L1 | Fast, low fees |
| `bsc` | BNB Smart Chain | L1 | High volume, minimal fees |
| `ethereum` | Ethereum | L1 | Security reference baseline |

---

## Scoring Formula

```python
score = (
    safety_score      * 0.35 +   # TVL, hack history, audits, validator decentralization
    reliability_score * 0.30 +   # uptime 24h/7d, finality time, block reorgs
    cost_score        * 0.25 +   # current gas, 7d avg, p90 fee
    speed_score       * 0.10     # TPS, confirmation time, congestion index
)
# Result: 0–100 float, higher = better for transactions
```

Weights are configurable via `src/scoring/weights.py`. Never hardcode them elsewhere.

---

## Key Design Decisions

### 1. MCP is the primary interface, REST is secondary
AI agents consume via MCP tools. REST exists for human developers and dashboards. When in doubt, prioritize MCP ergonomics.

### 2. Scores are pre-computed, not on-demand
Scores are recalculated every 60s via Celery and cached in Redis. API endpoints never trigger score computation — they only read from cache. This ensures <50ms response times.

### 3. Data source redundancy
Every critical metric (gas, uptime, TVL) must have at least 2 data sources. If primary fails, fallback silently. Log the failure.

### 4. Transparency by default
The scoring methodology is public (`/docs/scoring-methodology`). AI agents can explain to users exactly why a network was recommended.

---

## MCP Tools Reference

### `get_best_network`
```
Input:  amount_usd (float), asset (str), priority ("cost"|"speed"|"safety"|"balanced")
Output: {network, score, estimated_fee_usd, estimated_time_seconds, reasoning}
```

### `compare_networks`
```
Input:  networks (list[str]), amount_usd (float), asset (str)
Output: {comparison_table: [{network, score, fee_usd, time_s, safety_level}]}
```

### `estimate_transaction_cost`
```
Input:  network (str), amount_usd (float), token (str)
Output: {fee_usd, fee_native, fee_percentile, estimated_confirmation_seconds}
```

### `simulate_transaction`
```
Input:  from_network (str), to_network (str), amount_usd (float), asset (str)
Output: {steps, total_fee_usd, total_time_seconds, bridge_used, risks}
```

### `get_network_alerts`
```
Input:  networks (list[str] | None)
Output: {alerts: [{network, severity, type, message, started_at}]}
```

---

## Cache TTL Policy

```python
TTL_GAS_CURRENT     = 15    # seconds — gas changes constantly
TTL_NETWORK_SCORE   = 60    # seconds — scores update every minute
TTL_TVL             = 300   # seconds — 5 minutes
TTL_UPTIME          = 120   # seconds — 2 minutes
TTL_INCIDENTS       = 30    # seconds — alerts must be near real-time
TTL_HISTORICAL      = 3600  # seconds — 1 hour for historical data
```

---

## Environment Variables

```bash
# API
API_SECRET_KEY=
DEBUG=false
ENVIRONMENT=development  # development | staging | production

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/crypto_api

# Redis
REDIS_URL=redis://localhost:6379/0

# External APIs (all free tier to start)
COINGECKO_API_KEY=          # optional, increases rate limits
DEFILLAMA_BASE_URL=https://api.llama.fi

# MCP
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8001
```

---

## Development Commands

```bash
# Start full local stack
docker compose up -d

# Run API in dev mode (hot reload)
uv run uvicorn src.main:app --reload --port 8000

# Run MCP server
uv run python -m src.mcp.server

# Run tests
uv run pytest tests/ -v

# Run specific test
uv run pytest tests/unit/test_scoring.py -v

# Check API docs
open http://localhost:8000/docs

# Redis CLI
docker exec -it crypto-api-redis redis-cli
```

---

## Coding Conventions

- **Python 3.12+** — use modern syntax (`match`, `TypeAlias`, etc.)
- **Async everywhere** — all I/O must be `async/await`, no blocking calls
- **Pydantic v2** — for all data validation and serialization
- **Type hints required** — every function must have full type annotations
- **No print()** — use `structlog` for all logging
- **Error handling** — never swallow exceptions silently; log + re-raise or return typed error
- **Tests required** — every scoring dimension and MCP tool must have unit tests

---

## External Data Sources

| Provider | Data | Endpoint | Rate Limit (free) |
|----------|------|----------|-------------------|
| DefiLlama | TVL per chain | `api.llama.fi/chains` | No limit |
| CoinGecko | Market data | `api.coingecko.com/api/v3` | 30 req/min |
| L2Beat | L2 security metrics | `l2beat.com/api` | Public |
| Public RPCs | Gas, block data | Per-network RPC URLs | Varies |
| BlockNative | Gas predictions | `api.blocknative.com` | 1000 req/day free |

---

## What This API is NOT

- ❌ Not a price feed (use CoinGecko for that)
- ❌ Not a trading API (use CCXT for that)
- ❌ Not a wallet or transaction executor (read-only intelligence only)
- ❌ Not an AML/compliance tool (use AnChain.AI for that)

This API answers exactly one question: **"Which network should I use for this transaction, and why?"**

---

## Security Rules

1. **API keys solo como hash SHA-256 en DB, nunca texto plano**
   - Nunca almacenar claves de API en texto plano
   - Usar SHA-256 con salt para el hash
   - Validar comparando hashes, no texto plano

2. **Rate limiting por key con respuesta 429 + Retry-After**
   - Implementar rate limiting por API key
   - Responder con código 429 y header `Retry-After` cuando se exceda el límite
   - Definir límites por tier (free, basic, premium)

3. **Todo input validado con Pydantic antes de procesarse**
   - Todos los endpoints REST deben usar modelos Pydantic para request/response
   - Validación automática con FastAPI

4. **Whitelist estricta para el parámetro network (solo los 8 IDs definidos)**
   - Validar contra lista permitida: `solana`, `polygon`, `arbitrum`, `base`, `optimism`, `avalanche`, `bsc`, `ethereum`
   - Rechazar cualquier valor que no esté en la whitelist

5. **Timeout de 5 segundos en todas las llamadas a providers externos**
   - Todos los HTTP clients deben tener timeout configurado
   - Usar `httpx` con `timeout=5.0` o similar

6. **Circuit breaker si un provider falla 3 veces consecutivas**
   - Implementar circuit breaker pattern
   - Después de 3 fallos consecutivos, abrir el circuito
   - Retry automático después de un período de recuperación

7. **Nunca exponer stack traces en producción**
   - Configurar `DEBUG=false` en producción
   - Devolver mensajes de error genéricos al cliente
   - Loguear detalles internamente

8. **Cero secrets en código, todo por variables de entorno**
   - Nunca hardcodear credenciales
   - Usar `pydantic-settings` para configuración
   - Validar que variables requeridas existan al iniciar

9. **Redis y PostgreSQL sin acceso público, solo red interna Docker**
   - Configurar servicios en docker-compose con red interna
   - No exponer puertos al host a menos que sea necesario para desarrollo
   - Usar `127.0.0.1` o nombre del servicio como host

10. **HTTPS obligatorio, redirigir HTTP**
    - Configurar middleware para redirigir HTTP a HTTPS
    - Usar proxy reverso (nginx/traefik) en producción

11. **Validar inputs en cada MCP tool con Pydantic**
    - Cada MCP tool debe definir modelo de input con Pydantic
    - Validar antes de ejecutar cualquier lógica

---

## Monetization Rules

### Tiers

- **FREE**: 10k requests/mes, solo 4 redes (ethereum, polygon, arbitrum, solana), sin acceso a /v1/networks/best ni /v1/transactions/simulate, sin acceso MCP
- **PRO**: 500k requests/mes, todas las redes, todos los endpoints, acceso MCP incluido — $49/mes
- **ENTERPRISE**: ilimitado, todas las redes, endpoints custom, SLA 99.9%, acceso MCP prioritario — $299/mes

### Plan Enforcement

- FREE networks: `ethereum`, `polygon`, `arbitrum`, `solana` (solo estos 4)
- PRO/ENTERPRISE: todas las redes incluyendo `base`, `optimism`, `avalanche`, `bsc`
- Simulate endpoint requiere PRO o superior (403 con `upgrade_url`)
- MCP acceso solo en PRO y ENTERPRISE
- Headers obligatorios en responses: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `X-Plan-Tier`
- 403 response para endpoints de pago:
  ```json
  {"error": "plan_required", "required_plan": "PRO", "upgrade_url": "/pricing"}
  ```
