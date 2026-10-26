import pytest
import tempfile
import os
import json
from tokenomics import TokenomicsModeler, TokenModel

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def temp_config():
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
        json.dump({"simulation_horizon_months": 12, "monte_carlo_runs": 10}, f)
        config_path = f.name
    yield config_path
    if os.path.exists(config_path):
        os.unlink(config_path)

@pytest.fixture
def modeler(temp_db, temp_config):
    return TokenomicsModeler(db_path=temp_db, config_path=temp_config)

def test_create_model(modeler):
    model = modeler.create_model(
        name="Test Token",
        symbol="TEST",
        chain="ethereum",
        total_supply=1_000_000_000,
        circulating_supply=100_000_000,
        emission_schedule={"type": "linear", "annual_rate": 0.1},
        vesting_schedules=[{"type": "linear", "amount": 50_000_000, "months": 24}],
        utility_mechanisms=["staking", "governance"]
    )
    assert model.symbol == "TEST"
    assert model.total_supply == 1_000_000_000
    assert model.circulating_supply == 100_000_000

def test_get_model(modeler):
    model = modeler.create_model(
        "Test", "TEST", "ethereum", 1_000_000_000, 100_000_000,
        {"type": "none"}, [], []
    )
    retrieved = modeler.get_model(model.id)
    assert retrieved is not None
    assert retrieved.id == model.id
    assert retrieved.name == "Test"

def test_list_models(modeler):
    modeler.create_model("Token1", "TK1", "ethereum", 1_000_000, 100_000, {"type": "none"}, [], [])
    modeler.create_model("Token2", "TK2", "polygon", 2_000_000, 200_000, {"type": "none"}, [], [])
    models = modeler.list_models()
    assert len(models) >= 2

def test_simulate_base_scenario(modeler):
    model = modeler.create_model(
        "Test", "TEST", "ethereum", 1_000_000_000, 100_000_000,
        {"type": "linear", "annual_rate": 0.1}, [], []
    )
    result = modeler.simulate_price(model, "base", 12)
    assert result.scenario == "base"
    assert len(result.price_projection) == 12
    assert "month_1" in result.price_projection
    assert "month_12" in result.price_projection
    assert result.key_metrics["final_price"] > 0

def test_simulate_bear_bull(modeler):
    model = modeler.create_model(
        "Test", "TEST", "ethereum", 1_000_000_000, 100_000_000,
        {"type": "none"}, [], []
    )
    bear = modeler.simulate_price(model, "bear", 12)
    bull = modeler.simulate_price(model, "bull", 12)
    base = modeler.simulate_price(model, "base", 12)
    
    # Bear should have lower final price than base, bull higher
    assert bear.key_metrics["final_price"] < base.key_metrics["final_price"]
    assert bull.key_metrics["final_price"] > base.key_metrics["final_price"]

def test_monte_carlo(modeler):
    model = modeler.create_model(
        "Test", "TEST", "ethereum", 1_000_000_000, 100_000_000,
        {"type": "none"}, [], []
    )
    result = modeler.run_monte_carlo(model, 20)
    assert "mean" in result
    assert "median" in result
    assert "percentile_5" in result
    assert "percentile_95" in result
    assert result["min"] <= result["mean"] <= result["max"]

def test_save_simulation(modeler):
    model = modeler.create_model(
        "Test", "TEST", "ethereum", 1_000_000_000, 100_000_000,
        {"type": "none"}, [], []
    )
    result = modeler.simulate_price(model, "base", 12)
    modeler.save_simulation(result)
    
    simulations = modeler.get_simulations(model.id)
    assert len(simulations) >= 1
    assert simulations[0].scenario == "base"