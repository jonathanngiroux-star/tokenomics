# Tokenomics Modeling

Recurring model updates as token parameters evolve.

## Service Description

Tokenomics provides continuous token economics modeling and simulation:

- **Dynamic supply modeling** — Emission schedules, vesting unlocks, burns
- **Price simulation** — Bear/base/bull scenarios with demand/supply dynamics
- **Monte Carlo analysis** — Probabilistic projections with confidence intervals
- **Vesting schedule tracking** — Team, investor, community allocations
- **Utility mechanism analysis** — Staking, governance, fee capture, buybacks
- **Scenario planning** — Stress testing under various market conditions

Pricing: **$150–300/mo** (Accountability/Specialty tier)

## Installation

```bash
git clone https://github.com/jonathanngiroux-star/tokenomics
cd tokenomics
pip install -r requirements.txt
# or
pip install git+https://github.com/jonathanngiroux-star/tokenomics
```

## Configuration

```json
{
  "simulation_horizon_months": 36,
  "monte_carlo_runs": 1000,
  "price_sources": ["coingecko", "coinmarketcap"]
}
```

## CLI Interface

```bash
# Create token model
tokenomics create --name "MyToken" --symbol MTK --chain ethereum \
  --total-supply 1000000000 --circulating-supply 100000000 \
  --emission-type linear --emission-rate 0.15 \
  --vesting '{"type": "linear", "amount": 50000000, "months": 24}'

# Run simulation
tokenomics simulate mtk-20240115 --scenario base --horizon 36

# Monte Carlo analysis
tokenomics monte-carlo mtk-20240115 --runs 500

# List models
tokenomics list

# Get model details
tokenomics get mtk-20240115
```

## Emission Types

| Type | Parameters | Description |
|------|------------|-------------|
| `linear` | `annual_rate` | Fixed percentage of total supply per year |
| `exponential` | `monthly_rate` | Compounding monthly emission |
| `none` | — | No new emissions |

## Vesting Schedule Format

```json
{
  "type": "linear",
  "amount": 50000000,
  "months": 24
}
```

## Simulation Outputs

- Price projection (monthly for horizon)
- Supply projection (including emissions + vesting)
- Market cap projection
- Key metrics: final price, supply, market cap, total emission, vesting unlock

## Monte Carlo

Probabilistic simulation across bear/base/bull scenarios with percentile outputs (5th, 50th, 95th).

## Pricing

| Tier | Price | Includes |
|------|-------|----------|
| Starter | $150/mo | 5 models, 36-month horizon, 100 MC runs |
| Professional | $225/mo | 20 models, 60-month horizon, 1000 MC runs |
| Enterprise | $300/mo | Unlimited, custom scenarios, API access |

## Hosted Version

Managed tokenomics at **katsironni.com/tokenomics** — includes real-time price feeds, automated rebalancing alerts.

## License

MIT — see [LICENSE](LICENSE)