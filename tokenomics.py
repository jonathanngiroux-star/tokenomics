#!/usr/bin/env python3
"""
Tokenomics Modeling - Recurring model updates as token parameters evolve.
"""

import json
import sqlite3
import numpy as np
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import argparse
import sys
import math


@dataclass
class TokenModel:
    id: str
    name: str
    symbol: str
    chain: str
    total_supply: float
    circulating_supply: float
    emission_schedule: Dict[str, Any]
    vesting_schedules: List[Dict]
    utility_mechanisms: List[str]
    created_at: str
    updated_at: str


@dataclass
class SimulationResult:
    model_id: str
    timestamp: str
    scenario: str
    price_projection: Dict[str, float]
    supply_projection: Dict[str, float]
    market_cap_projection: Dict[str, float]
    key_metrics: Dict[str, float]


class TokenomicsModeler:
    def __init__(self, db_path: str = "./tokenomics.db", config_path: str = "./config.json"):
        self.db_path = db_path
        self.config_path = config_path
        self.config = self._load_config()
        self._init_db()

    def _load_config(self) -> Dict:
        if Path(self.config_path).exists():
            with open(self.config_path) as f:
                return json.load(f)
        return {
            "default_chain": "ethereum",
            "simulation_horizon_months": 36,
            "monte_carlo_runs": 1000,
            "price_sources": ["coingecko", "coinmarketcap"],
        }

    def _save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    chain TEXT NOT NULL,
                    total_supply REAL NOT NULL,
                    circulating_supply REAL NOT NULL,
                    emission_schedule TEXT NOT NULL,
                    vesting_schedules TEXT NOT NULL,
                    utility_mechanisms TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS simulations (
                    id TEXT PRIMARY KEY,
                    model_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    price_projection TEXT NOT NULL,
                    supply_projection TEXT NOT NULL,
                    market_cap_projection TEXT NOT NULL,
                    key_metrics TEXT NOT NULL
                )
            """)

    def create_model(self, name: str, symbol: str, chain: str, total_supply: float,
                     circulating_supply: float, emission_schedule: Dict,
                     vesting_schedules: List[Dict], utility_mechanisms: List[str]) -> TokenModel:
        model_id = f"{symbol.lower()}-{datetime.now().strftime('%Y%m%d')}"
        now = datetime.now().isoformat()
        model = TokenModel(
            id=model_id,
            name=name,
            symbol=symbol,
            chain=chain,
            total_supply=total_supply,
            circulating_supply=circulating_supply,
            emission_schedule=emission_schedule,
            vesting_schedules=vesting_schedules,
            utility_mechanisms=utility_mechanisms,
            created_at=now,
            updated_at=now,
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO models (id, name, symbol, chain, total_supply, circulating_supply,
                                  emission_schedule, vesting_schedules, utility_mechanisms,
                                  created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (model.id, model.name, model.symbol, model.chain, model.total_supply,
                  model.circulating_supply, json.dumps(model.emission_schedule),
                  json.dumps(model.vesting_schedules), json.dumps(model.utility_mechanisms),
                  model.created_at, model.updated_at))
        return model

    def get_model(self, model_id: str) -> Optional[TokenModel]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
            if row:
                return TokenModel(
                    id=row['id'], name=row['name'], symbol=row['symbol'], chain=row['chain'],
                    total_supply=row['total_supply'], circulating_supply=row['circulating_supply'],
                    emission_schedule=json.loads(row['emission_schedule']),
                    vesting_schedules=json.loads(row['vesting_schedules']),
                    utility_mechanisms=json.loads(row['utility_mechanisms']),
                    created_at=row['created_at'], updated_at=row['updated_at']
                )
        return None

    def list_models(self) -> List[TokenModel]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM models").fetchall()
            return [TokenModel(
                id=r['id'], name=r['name'], symbol=r['symbol'], chain=r['chain'],
                total_supply=r['total_supply'], circulating_supply=r['circulating_supply'],
                emission_schedule=json.loads(r['emission_schedule']),
                vesting_schedules=json.loads(r['vesting_schedules']),
                utility_mechanisms=json.loads(r['utility_mechanisms']),
                created_at=r['created_at'], updated_at=r['updated_at']
            ) for r in rows]

    def simulate_price(self, model: TokenModel, scenario: str = "base",
                       horizon_months: int = None) -> SimulationResult:
        if horizon_months is None:
            horizon_months = self.config.get("simulation_horizon_months", 36)

        # Simple simulation logic
        current_price = 1.0  # Would fetch from price source
        current_supply = model.circulating_supply
        
        # Emission impact
        monthly_emission = 0
        if model.emission_schedule.get("type") == "linear":
            monthly_emission = model.emission_schedule.get("annual_rate", 0) / 12 * model.total_supply
        elif model.emission_schedule.get("type") == "exponential":
            monthly_emission = model.emission_schedule.get("monthly_rate", 0) * current_supply

        # Vesting unlock impact
        monthly_vesting = 0
        for vest in model.vesting_schedules:
            if vest.get("type") == "linear":
                monthly_vesting += vest.get("amount", 0) / vest.get("months", 1)

        price_projection = {}
        supply_projection = {}
        market_cap_projection = {}

        # Scenario multipliers
        multipliers = {
            "bear": 0.7,
            "base": 1.0,
            "bull": 1.5,
        }
        mult = multipliers.get(scenario, 1.0)

        for month in range(1, horizon_months + 1):
            current_supply += monthly_emission + monthly_vesting
            # Simple price model: demand growth vs supply inflation
            demand_growth = 0.02 * mult  # 2% monthly demand growth
            supply_inflation = (monthly_emission + monthly_vesting) / max(current_supply, 1)
            price_change = demand_growth - supply_inflation
            current_price *= (1 + price_change)
            
            price_projection[f"month_{month}"] = round(current_price, 4)
            supply_projection[f"month_{month}"] = round(current_supply, 2)
            market_cap_projection[f"month_{month}"] = round(current_price * current_supply, 2)

        key_metrics = {
            "final_price": price_projection.get(f"month_{horizon_months}", 0),
            "final_supply": supply_projection.get(f"month_{horizon_months}", 0),
            "final_market_cap": market_cap_projection.get(f"month_{horizon_months}", 0),
            "total_emission": monthly_emission * horizon_months,
            "total_vesting_unlock": monthly_vesting * horizon_months,
            "price_change_pct": (current_price - 1.0) / 1.0 * 100,
        }

        return SimulationResult(
            model_id=model.id,
            timestamp=datetime.now().isoformat(),
            scenario=scenario,
            price_projection=price_projection,
            supply_projection=supply_projection,
            market_cap_projection=market_cap_projection,
            key_metrics=key_metrics,
        )

    def run_monte_carlo(self, model: TokenModel, runs: int = None) -> Dict[str, Any]:
        if runs is None:
            runs = self.config.get("monte_carlo_runs", 1000)
        
        results = []
        for _ in range(min(runs, 100)):  # Cap for performance
            scenario = np.random.choice(["bear", "base", "bull"], p=[0.2, 0.6, 0.2])
            result = self.simulate_price(model, scenario)
            results.append(result.key_metrics["final_price"])
        
        return {
            "mean": float(np.mean(results)),
            "median": float(np.median(results)),
            "std": float(np.std(results)),
            "percentile_5": float(np.percentile(results, 5)),
            "percentile_95": float(np.percentile(results, 95)),
            "min": float(np.min(results)),
            "max": float(np.max(results)),
        }

    def save_simulation(self, result: SimulationResult):
        sim_id = f"{result.model_id}-{result.scenario}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO simulations (id, model_id, timestamp, scenario,
                                       price_projection, supply_projection,
                                       market_cap_projection, key_metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sim_id, result.model_id, result.timestamp, result.scenario,
                  json.dumps(result.price_projection), json.dumps(result.supply_projection),
                  json.dumps(result.market_cap_projection), json.dumps(result.key_metrics)))

    def get_simulations(self, model_id: str) -> List[SimulationResult]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM simulations WHERE model_id = ? ORDER BY timestamp DESC", (model_id,)).fetchall()
            return [SimulationResult(
                model_id=r['model_id'], timestamp=r['timestamp'], scenario=r['scenario'],
                price_projection=json.loads(r['price_projection']),
                supply_projection=json.loads(r['supply_projection']),
                market_cap_projection=json.loads(r['market_cap_projection']),
                key_metrics=json.loads(r['key_metrics'])
            ) for r in rows]


def main():
    parser = argparse.ArgumentParser(description="Tokenomics Modeling")
    parser.add_argument("-c", "--config", default="./config.json")
    parser.add_argument("-d", "--db", default="./tokenomics.db")
    subparsers = parser.add_subparsers(dest="action", required=True)

    create_parser = subparsers.add_parser("create", help="Create token model")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--symbol", required=True)
    create_parser.add_argument("--chain", default="ethereum")
    create_parser.add_argument("--total-supply", type=float, required=True)
    create_parser.add_argument("--circulating-supply", type=float, required=True)
    create_parser.add_argument("--emission-type", choices=["linear", "exponential", "none"], default="linear")
    create_parser.add_argument("--emission-rate", type=float, default=0.1)  # annual
    create_parser.add_argument("--vesting", action="append", help="JSON vesting schedule")

    simulate_parser = subparsers.add_parser("simulate", help="Run simulation")
    simulate_parser.add_argument("model_id")
    simulate_parser.add_argument("--scenario", choices=["bear", "base", "bull"], default="base")
    simulate_parser.add_argument("--horizon", type=int, default=36)

    monte_parser = subparsers.add_parser("monte-carlo", help="Monte Carlo simulation")
    monte_parser.add_argument("model_id")
    monte_parser.add_argument("--runs", type=int, default=100)

    list_parser = subparsers.add_parser("list", help="List models")
    get_parser = subparsers.add_parser("get", help="Get model details")
    get_parser.add_argument("model_id")

    args = parser.parse_args()

    modeler = TokenomicsModeler(db_path=args.db, config_path=args.config)

    if args.action == "create":
        emission_schedule = {"type": args.emission_type}
        if args.emission_type != "none":
            emission_schedule["annual_rate" if args.emission_type == "linear" else "monthly_rate"] = args.emission_rate

        vesting_schedules = []
        if args.vesting:
            for v in args.vesting:
                vesting_schedules.append(json.loads(v))

        model = modeler.create_model(
            args.name, args.symbol, args.chain, args.total_supply, args.circulating_supply,
            emission_schedule, vesting_schedules, []
        )
        print(f"Created model: {model.name} ({model.symbol}) - ID: {model.id}")

    elif args.action == "simulate":
        model = modeler.get_model(args.model_id)
        if not model:
            print(f"Model {args.model_id} not found")
            sys.exit(1)
        result = modeler.simulate_price(model, args.scenario, args.horizon)
        modeler.save_simulation(result)
        print(json.dumps(asdict(result), indent=2))

    elif args.action == "monte-carlo":
        model = modeler.get_model(args.model_id)
        if not model:
            print(f"Model {args.model_id} not found")
            sys.exit(1)
        result = modeler.run_monte_carlo(model, args.runs)
        print(json.dumps(result, indent=2))

    elif args.action == "list":
        models = modeler.list_models()
        for m in models:
            print(f"{m.id} | {m.name} ({m.symbol}) | {m.chain} | Supply: {m.circulating_supply:,.0f}/{m.total_supply:,.0f}")

    elif args.action == "get":
        model = modeler.get_model(args.model_id)
        if model:
            print(json.dumps(asdict(model), indent=2))
        else:
            print(f"Model {args.model_id} not found")


if __name__ == "__main__":
    main()