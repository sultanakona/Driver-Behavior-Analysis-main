# run_sim.py
from __future__ import annotations
import os, sys, time, csv, random, argparse, subprocess
from typing import Dict, List
from dotenv import load_dotenv

import traci
from sumolib import checkBinary

from llm_client import LLMClient
from scenario_generator import create_scenario_spec, write_routes_xml
from risk_metrics import ttc
from behavior_agents import LLMBehaviorManager

def pick_llm_controlled(traci, fraction: float, persona_name: str) -> List[str]:
    vids = list(traci.vehicle.getIDList())
    random.shuffle(vids)
    k = max(0, int(len(vids) * fraction))
    return vids[:k]

def run(args):
    load_dotenv()

    llm = LLMClient(model=args.llm_model, temperature=args.temperature)

    # 1) Scenario spec
    spec = create_scenario_spec(args.net, args.scenario, llm)
    os.makedirs(args.out, exist_ok=True)
    rou = os.path.join(args.out, "generated.rou.xml")
    write_routes_xml(spec, rou)

    # 2) Launch SUMO
    sumoBinary = checkBinary("sumo-gui" if args.gui else "sumo")
    sumo_cmd = [sumoBinary, "-n", args.net, "-r", rou, "--start", "--quit-on-end", "--step-length", str(args.step)]
    # weather proxy via speed dev on all vehicles (global factor using speed factor on depart handled via vType)
    print("[INFO] Launch:", " ".join(sumo_cmd))
    traci.start(sumo_cmd)

    # 3) Persona assignment per departing vehicle
    persona_names, persona_fracs = [p.name for p in spec.personas], [p.fraction for p in spec.personas]
    persona_of: Dict[str, str] = {}
    llm_controlled: set[str] = set()

    # 4) Behavior manager (LLM-driven)
    beh_mgr = LLMBehaviorManager(
        llm=llm, weather_label=spec.weather.label, weather_sf=spec.weather.speedFactor,
        persona_map=persona_of, decision_period=args.decision_period
    )

    # 5) Risk logging
    log_path = os.path.join(args.out, "risk_log.csv")
    with open(log_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["step","veh","leader","gap_m","vf","vl","ttc_s","label"])
        # writer.writerow(["step","veh","leader","gap_m","vf","vl","ttc_s"])

        step = 0
        try:
            while traci.simulation.getMinExpectedNumber() > 0:
                traci.simulationStep()

                # newly departed -> assign persona; maybe mark as LLM-controlled
                for v in traci.simulation.getDepartedIDList():
                    persona = random.choices(persona_names, weights=persona_fracs, k=1)[0]
                    persona_of[v] = persona
                    # Optional: immutably set type to persona's vType (already bound by flow 'type')
                    # Decide LLM control for a subset only once at depart (global target fraction)
                    if random.random() < spec.llmAgentFraction:
                        llm_controlled.add(v)

                # execute behavior for all LLM-controlled vehicles
                beh_mgr.step(traci, step)

                # risk metrics (near-miss via TTC)
                for v in traci.vehicle.getIDList():
                    leader = traci.vehicle.getLeader(v)
                    if leader:
                        lead_id, gap = leader
                        vf = traci.vehicle.getSpeed(v)
                        vl = traci.vehicle.getSpeed(lead_id)
                        val = ttc(gap, vf, vl)
                        if val is not None:
                            label = 1 if val < 1.5 else 0  # 1=risky, 0=normal
                            writer.writerow([step, v, lead_id, f"{gap:.2f}", f"{vf:.2f}", f"{vl:.2f}", f"{val:.2f}", label])

                        # if val is not None and val < 1.5:  # near-miss threshold
                        #     writer.writerow([step, v, lead_id, f"{gap:.2f}", f"{vf:.2f}", f"{vl:.2f}", f"{val:.2f}"])

                step += 1

        finally:
            traci.close(False)
            print(f"[INFO] Finished. Risk log: {log_path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", required=True, help="Path to SUMO net.net.xml")
    ap.add_argument("--scenario", default="Evening peak with light rain; many buses and rickshaws; impatient drivers at the west approach.",
                    help="Natural language brief to seed scenario generation")
    ap.add_argument("--out", default="out", help="Output directory")
    ap.add_argument("--gui", action="store_true", help="Use sumo-gui")
    ap.add_argument("--step", type=float, default=1.0, help="SUMO step-length seconds")
    ap.add_argument("--decision-period", type=int, default=5, help="Strategic LLM decision period (s)")
    ap.add_argument("--llm-model", default="gemini-2.5-flash")
    ap.add_argument("--temperature", type=float, default=0.2)
    args = ap.parse_args()
    run(args)

