"""
Registro central de las 5 restricciones de seguridad oficiales, en el orden
recomendado por el prompt (estructura -> oficiales -> disponibilidad -> ruta
-> tiempo -> viabilidad económica). Ver decision_engine.py para el resto del
pipeline (disponibilidad, ruta, económico van fuera de esta lista porque no
son "restricciones de seguridad" del protocolo oficial).
"""
from constraints.flagged_zone_night import FlaggedZoneNightConstraint
from constraints.heat_rule import HeatRuleConstraint
from constraints.mandatory_break import MandatoryBreakConstraint
from constraints.shift_end_infeasible import ShiftEndInfeasibleConstraint
from constraints.vehicle_capacity import VehicleCapacityConstraint

OFFICIAL_SAFETY_CONSTRAINTS = [
    FlaggedZoneNightConstraint(),
    MandatoryBreakConstraint(),
    HeatRuleConstraint(),
    ShiftEndInfeasibleConstraint(),
    VehicleCapacityConstraint(),
]

__all__ = ["OFFICIAL_SAFETY_CONSTRAINTS"]
