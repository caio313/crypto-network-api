# Crypto Network Decision API

> Which blockchain network should I use for this transaction — and why?

An AI-first API that answers the one question no existing tool does: given an amount, an asset, and a priority, which network is the safest, most reliable, and cheapest option right now?

Built for AI agents, with a native MCP layer.

---

## The Problem

Sending $500 USDC across blockchain networks can cost anywhere from $0.01 to $40 depending on the network, time of day, and current congestion. No tool gives AI agents a clear, real-time answer on which network to use and why.

## The Solution

A scoring engine that combines safety, reliability, cost, and speed into a single 0–100 score per network — updated in real time. AI agents query it directly via MCP and get a recommendation with full reasoning.

---

## Networks

Ethereum · Arbitrum · Base · Optimism · Polygon · Solana · Avalanche · BSC

---

## For AI Agents — MCP Tools

Connect your agent directly via MCP. Available on all plans.

| Tool | FREE | PRO | ENTERPRISE |
|------|------|-----|------------|
| `estimate_cost` — exact fee in USD before sending | ✅ | ✅ | ✅ |
| `get_alerts` — check for congestion or incidents | ✅ | ✅ | ✅ |
| `get_best_network` — optimal network with reasoning | ❌ | ✅ | ✅ |
| `compare_networks` — compare networks side by side | ❌ | ✅ | ✅ |
| `simulate_transaction` — full simulation with bridges | ❌ | ✅ | ✅ |

---

## REST API

GET  /v1/networks/scores         Real-time network ranking
GET  /v1/networks/best           Best network for your transaction (PRO)
POST /v1/transactions/estimate   Estimate transaction cost
POST /v1/transactions/simulate   Full simulation with bridges (PRO)
GET  /v1/gas/current             Gas prices across all networks
GET  /v1/gas/{network}/predict   Gas prediction next 1h/3h/6h (PRO)
GET  /v1/alerts/active           Active network alerts
GET  /mcp                        MCP endpoint for AI agents (PRO)


---

## Pricing

| Tier | Requests | Networks | MCP Access | Price |
|------|----------|----------|------------|-------|
| FREE | 100/day | 4 networks | estimate_cost + get_alerts | $0 |
| PRO | 2,000/day | All 8 networks | All tools | 30-day free trial, then $5/mo + $0.029/req |
| ENTERPRISE | Unlimited | All + custom | All tools + priority | $159/mo |

> PRO trial includes full access for 30 days — no credit card required.

Get your API key → https://cryptonetworkapi.com/pricing

---

## Quick Start
```bash
cp .env.example .env
docker compose up -d
```

API docs available at `http://localhost:8000/docs`

---

## License

MIT
