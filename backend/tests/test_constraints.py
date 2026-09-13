"""Al menos una prueba por cada restricción oficial de seguridad, y una
donde efectivamente se activa (sección 26 del prompt)."""
from datetime import datetime, timedelta

from constraints.base import RouteEstimate
from constraints.flagged_zone_night import FlaggedZoneNightConstraint
from constraints.heat_rule import HeatRuleConstraint
from constraints.mandatory_break import MandatoryBreakConstraint
from constraints.shift_end_infeasible import ShiftEndInfeasibleConstraint
from constraints.vehicle_capacity import VehicleCapacityConstraint
from domain_models import AgentState, CourierState, Order, ShiftConfig

BASE_ORDER_KWARGS = dict(
    order_id="ORD-C", platform="rappi",
    zone_pickup=5, zone_dropoff=5,
    zone_pickup_name="z5", zone_dropoff_name="z5",
    distance_pickup_km=1.0, distance_delivery_km=2.0,
    base_pay_mxn=50.0, est_tip_mxn=5.0, surge_multiplier=1.0,
    restaurant_prep_min=5.0, weight_kg=1.0, volume_liters=2.0, vehicle="moto",
)


def _order(sim_time: datetime, **overrides) -> Order:
    kwargs = dict(BASE_ORDER_KWARGS)
    kwargs.update(overrides)
    return Order(sim_time=sim_time, decision_deadline=sim_time + timedelta(seconds=5), **kwargs)


def _courier(shift_end_time: datetime, continuous_riding_min: float = 0.0) -> CourierState:
    config = ShiftConfig(
        seed=1, shift_hours=8, vehicle="moto", start_location_zone=5,
        sim_start_time=shift_end_time - timedelta(hours=8), shift_end_time=shift_end_time,
        final_destination_zone=5,
    )
    return CourierState(
        agent_id="test", strategy_name="NextMove", config=config, current_zone=5,
        sim_time=shift_end_time - timedelta(hours=1), state=AgentState.EVALUATING,
        continuous_riding_min=continuous_riding_min,
    )


def _route(**overrides) -> RouteEstimate:
    base = dict(pickup_min=5.0, dropoff_min=3.0, total_extra_time_min=10.0,
                total_extra_distance_km=1.0, arrival_at_final_destination=datetime(2026, 1, 1),
                blocked=False)
    base.update(overrides)
    return RouteEstimate(**base)


def test_flagged_zone_night_triggers():
    sim_time = datetime(2026, 3, 21, 22, 30, 0)  # después de las 22:00
    order = _order(sim_time, zone_dropoff=3)  # zona 3 está marcada en config
    courier = _courier(shift_end_time=sim_time + timedelta(hours=1))
    route = _route(arrival_at_final_destination=sim_time)
    result = FlaggedZoneNightConstraint().check(order, courier, route)
    assert result.passed is False
    assert result.reason_code == "flagged_zone_night"


def test_flagged_zone_night_passes_during_day():
    sim_time = datetime(2026, 3, 21, 14, 0, 0)
    order = _order(sim_time, zone_dropoff=3)
    courier = _courier(shift_end_time=sim_time + timedelta(hours=1))
    route = _route(arrival_at_final_destination=sim_time)
    result = FlaggedZoneNightConstraint().check(order, courier, route)
    assert result.passed is True


def test_mandatory_break_triggers():
    sim_time = datetime(2026, 3, 21, 12, 0, 0)
    order = _order(sim_time)
    courier = _courier(shift_end_time=sim_time + timedelta(hours=4), continuous_riding_min=235)
    route = _route(pickup_min=5, dropoff_min=3)
    result = MandatoryBreakConstraint().check(order, courier, route)
    assert result.passed is False
    assert result.reason_code == "mandatory_break"


def test_heat_rule_triggers_inside_window():
    sim_time = datetime(2026, 3, 21, 13, 0, 0)  # dentro de 12:00-16:00
    order = _order(sim_time)
    courier = _courier(shift_end_time=sim_time + timedelta(hours=4), continuous_riding_min=85)
    route = _route(pickup_min=5, dropoff_min=3)
    result = HeatRuleConstraint().check(order, courier, route)
    assert result.passed is False
    assert result.reason_code == "heat_rule"


def test_heat_rule_does_not_apply_outside_window():
    sim_time = datetime(2026, 3, 21, 20, 0, 0)  # fuera de la ventana
    order = _order(sim_time)
    courier = _courier(shift_end_time=sim_time + timedelta(hours=4), continuous_riding_min=85)
    route = _route(pickup_min=5, dropoff_min=3)
    result = HeatRuleConstraint().check(order, courier, route)
    assert result.passed is True


def test_shift_end_infeasible_triggers():
    shift_end = datetime(2026, 3, 21, 20, 0, 0)
    sim_time = shift_end - timedelta(minutes=10)
    order = _order(sim_time)
    courier = _courier(shift_end_time=shift_end)
    route = _route(arrival_at_final_destination=shift_end + timedelta(minutes=12))
    result = ShiftEndInfeasibleConstraint().check(order, courier, route)
    assert result.passed is False
    assert result.reason_code == "shift_end_infeasible"


def test_vehicle_capacity_triggers():
    sim_time = datetime(2026, 3, 21, 12, 0, 0)
    order = _order(sim_time, weight_kg=999.0, volume_liters=999.0, vehicle="bike")
    courier = _courier(shift_end_time=sim_time + timedelta(hours=4))
    route = _route()
    result = VehicleCapacityConstraint().check(order, courier, route)
    assert result.passed is False
    assert result.reason_code == "vehicle_capacity"


def test_vehicle_capacity_passes_within_limits():
    sim_time = datetime(2026, 3, 21, 12, 0, 0)
    order = _order(sim_time, weight_kg=1.0, volume_liters=2.0, vehicle="car")
    courier = _courier(shift_end_time=sim_time + timedelta(hours=4))
    route = _route()
    result = VehicleCapacityConstraint().check(order, courier, route)
    assert result.passed is True


def test_safety_refusal_distinguishable_from_economic_refusal():
    """binding_constraint debe distinguir una negativa de seguridad de una
    económica (reservation_wage)."""
    from decide import handle_decide
    from models import DecideRequest

    safety_req = DecideRequest(
        order_id="ORD-SAFE", sim_time="2026-03-21T12:00:00", zone_pickup=1, zone_dropoff=1,
        distance_pickup_km=1.0, distance_delivery_km=1.0, base_pay_mxn=200.0, surge_multiplier=2.0,
        weight_kg=999.0, volume_liters=999.0, vehicle="bike",
    )
    econ_req = DecideRequest(
        order_id="ORD-ECON", sim_time="2026-03-21T12:00:00", zone_pickup=1, zone_dropoff=1,
        distance_pickup_km=0.1, distance_delivery_km=0.1, base_pay_mxn=1.0, surge_multiplier=1.0,
        weight_kg=0.5, volume_liters=0.5, vehicle="car",
    )
    safety_resp = handle_decide(safety_req)
    econ_resp = handle_decide(econ_req)

    assert safety_resp.decision == "SKIP" and safety_resp.binding_constraint == "vehicle_capacity"
    assert econ_resp.decision == "SKIP" and econ_resp.binding_constraint == "reservation_wage"
    assert safety_resp.binding_constraint != econ_resp.binding_constraint
