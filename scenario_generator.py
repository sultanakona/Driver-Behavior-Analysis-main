# scenario_generator.py
from __future__ import annotations
import random, xml.etree.ElementTree as ET
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from sumolib.net import readNet
from llm_client import LLMClient
from templates import SCENARIO_SYSTEM, SCENARIO_USER_TEMPLATE

# ---------- Pydantic Schemas ----------
class VType(BaseModel):
    tau: float = 1.2
    sigma: float = 0.5
    speedFactor: float = 1.0
    accel: float = 2.6
    decel: float = 4.5

class Persona(BaseModel):
    name: str
    fraction: float
    vType: VType

class Flow(BaseModel):
    id: str
    from_: str = Field(alias="from")   # ✅ fixed: trailing underscore, not leading
    to: str
    vehPerHour: int
    vTypePersona: str

class Weather(BaseModel):
    label: str = "clear"
    speedFactor: float = 1.0

class ScenarioSpec(BaseModel):
    sim: Dict[str, int] = {"begin":0, "end":3600}
    weather: Weather = Weather()
    personas: List[Persona]
    flows: List[Flow]
    llmAgentFraction: float = 0.15

# ---------- Utilities ----------
def sample_edge_ids(net_path: str, k: int = 20) -> List[str]:
    net = readNet(net_path)
    car_edges = [e.getID() for e in net.getEdges()]
    if len(car_edges) == 0:
        raise RuntimeError("No edges found in network.")
    return random.sample(car_edges, min(k, len(car_edges)))

def default_personas() -> List[Persona]:
    return [
        Persona(name="calm", fraction=0.5, vType=VType(tau=1.5, sigma=0.3, speedFactor=0.95)),
        Persona(name="distracted", fraction=0.3, vType=VType(tau=1.1, sigma=0.7, speedFactor=1.0)),
        Persona(name="aggressive", fraction=0.2, vType=VType(tau=0.9, sigma=0.6, speedFactor=1.08)),
    ]

def fallback_flows(edges: List[str], personas: List[Persona], n_flows: int = 4) -> List[Flow]:
    flows = []
    for i in range(n_flows):
        fr, to = random.sample(edges, 2)
        per = random.choice(personas).name
        flows.append(Flow(id=f"f{i}", **{"from": fr, "to": to}, vehPerHour=random.randint(300, 900), vTypePersona=per))
    return flows

# ---------- LLM-driven or fallback scenario creation ----------
def create_scenario_spec(net_path: str, brief: str, llm: LLMClient) -> ScenarioSpec:
    edge_list = "\n".join(sample_edge_ids(net_path, 30))
    user_msg = SCENARIO_USER_TEMPLATE.format(brief=brief, edge_list=edge_list)
    resp = llm.complete(SCENARIO_SYSTEM, user_msg, json_expected=True)

    if resp.parsed_json:
        try:
            return ScenarioSpec.model_validate(resp.parsed_json)
        except Exception:
            pass  # fall through to fallback

    # Fallback, deterministic but reasonable
    personas = default_personas()
    flows = fallback_flows(sample_edge_ids(net_path, 12), personas, n_flows=5)
    return ScenarioSpec(
        sim={"begin":0,"end":3600},
        weather=Weather(label="clear", speedFactor=0.98),
        personas=personas,
        flows=flows,
        llmAgentFraction=0.15
    )

# ---------- Write SUMO route file ----------
def write_routes_xml(spec: ScenarioSpec, out_path: str) -> None:
    root = ET.Element("routes")

    # vTypes from personas
    for p in spec.personas:
        v = p.vType
        ET.SubElement(root, "vType", {
            "id": p.name,
            "tau": f"{v.tau}",
            "sigma": f"{v.sigma}",
            "speedFactor": f"{v.speedFactor}",
            "accel": f"{v.accel}",
            "decel": f"{v.decel}",
            "lcStrategic": "1",
            "lcSpeedGain": "1",
            "lcCooperative": "0.5"
        })

    begin = spec.sim.get("begin", 0)
    end = spec.sim.get("end", 3600)

    # flows
    for fl in spec.flows:
        ET.SubElement(root, "flow", {
            "id": fl.id,
            "from": fl.from_,   # ✅ updated reference
            "to": fl.to,
            "begin": str(begin),
            "end": str(end),
            "vehsPerHour": str(fl.vehPerHour),
            "type": fl.vTypePersona
        })

    tree = ET.ElementTree(root)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)

