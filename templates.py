# templates.py
SCENARIO_SYSTEM = """You are a traffic scenario planner for SUMO. 
Given a natural-language brief and a list of available edges, produce a compact JSON spec for a 1-hour simulation.
Keep it valid JSON and concise.
"""

SCENARIO_USER_TEMPLATE = """
BRIEF:
{brief}

AVAILABLE_EDGES (sample, not exhaustive):
{edge_list}

Return JSON with fields:
- sim: {{"begin":0, "end":3600}}
- weather: {{"label":"clear|rain|storm", "speedFactor": float (0.7-1.1)}}
- personas: [{{"name":"calm|aggressive|distracted", "fraction":0-1, 
               "vType":{{"tau":float,"sigma":float,"speedFactor":float,"accel":2.6,"decel":4.5}} }}]
- flows: [{{"id":str,"from":edgeId,"to":edgeId,"vehPerHour":int,"vTypePersona":"one of persona names"}}]
- llmAgentFraction: float (0.0-0.5)  # fraction of vehicles controlled by LLM strategies
Ensure persona fractions sum ~1, pick 3-6 flows using listed edges, ensure fields present.
"""

BEHAVIOR_SYSTEM = """You produce **strategic** driving decisions for human-like agents.
Decide high-level intent every few seconds. Output compact JSON only.
Allowed 'action': ["maintain","slow_down","speed_up","change_left","change_right","overtake_if_possible"].
Return: {"action":str, "targetSpeedFactor": float (0.7-1.2), "desiredHeadway": float seconds (0.8-2.5)}
Be realistic and safe under poor weather or short gaps.
"""

BEHAVIOR_USER_TEMPLATE = """
Persona: {persona}
Weather: {weather} (speedFactor={w_factor})
State:
- speed_mps={v:.2f}, lane={lane}, lanes_total={lanes_total}
- leader_gap_m={gap:.1f}, leader_speed_mps={v_lead:.2f}
- tl_state_ahead={tl_state}
- local_density={density:.2f} veh/100m
Goal: reach destination safely but consistent with persona.
Respond JSON only with keys: action, targetSpeedFactor, desiredHeadway.
"""

