"""
agents.py — Multi-Agent AI Controller
======================================
Four agents collaborate to decide fan speed in AUTO mode.

  TemperatureAgent     → reads simulated temperature
  UserPreferenceAgent  → checks time of day (night → prefer LOW)
  EnergyAgent          → downgrades HIGH → MEDIUM to save energy
  CoordinatorAgent     → merges all outputs into a final speed
"""

import random
import logging
from datetime import datetime

logger = logging.getLogger("Agents")

SPEEDS = ["OFF", "LOW", "MEDIUM", "HIGH"]
RANK   = {s: i for i, s in enumerate(SPEEDS)}  # OFF=0, LOW=1, MEDIUM=2, HIGH=3


# ─────────────────────────────────────────────────────────────────────────────
# Individual Agents
# ─────────────────────────────────────────────────────────────────────────────

class TemperatureAgent:
    """Recommends fan speed based on temperature."""
    name = "TemperatureAgent"

    def decide(self, env: dict) -> str:
        temp = env["temperature"]
        if temp < 25:
            speed = "OFF"
        elif temp < 30:
            speed = "LOW"
        elif temp < 35:
            speed = "MEDIUM"
        else:
            speed = "HIGH"
        logger.info(f"[{self.name}] temp={temp:.1f}°C  →  {speed}")
        return speed


class UserPreferenceAgent:
    """At night (22:00–06:00) prefers LOW; no preference otherwise."""
    name = "UserPreferenceAgent"

    def decide(self, env: dict) -> str | None:
        hour = env["hour"]
        is_night = hour >= 22 or hour < 6
        if is_night:
            logger.info(f"[{self.name}] hour={hour}  night-time  →  cap at LOW")
            return "LOW"
        logger.info(f"[{self.name}] hour={hour}  day-time  →  no preference")
        return None


class EnergyAgent:
    """Downgrades HIGH → MEDIUM to conserve energy."""
    name = "EnergyAgent"

    def optimize(self, speed: str) -> str:
        if speed == "HIGH":
            logger.info(f"[{self.name}] HIGH  →  MEDIUM (energy saving)")
            return "MEDIUM"
        logger.info(f"[{self.name}] {speed}  →  accepted as-is")
        return speed


# ─────────────────────────────────────────────────────────────────────────────
# Coordinator Agent
# ─────────────────────────────────────────────────────────────────────────────

class CoordinatorAgent:
    """
    Combines all agent outputs and resolves conflicts.

    Priority rules (applied in order):
      1. TemperatureAgent gives the base recommendation.
      2. UserPreferenceAgent can cap it downward (night → max LOW).
      3. EnergyAgent can further reduce HIGH → MEDIUM.
    """

    def __init__(self):
        self.temp_agent   = TemperatureAgent()
        self.pref_agent   = UserPreferenceAgent()
        self.energy_agent = EnergyAgent()

    def decide(self, env: dict) -> str:
        logger.info(f"[Coordinator] env={env}")

        base = self.temp_agent.decide(env)
        pref = self.pref_agent.decide(env)

        candidate = base
        if pref is not None and RANK[candidate] > RANK[pref]:
            logger.info(f"[Coordinator] preference caps {candidate} → {pref}")
            candidate = pref

        final = self.energy_agent.optimize(candidate)
        logger.info(f"[Coordinator] FINAL DECISION → {final}")
        return final


# ─────────────────────────────────────────────────────────────────────────────
# Environment Simulator
# ─────────────────────────────────────────────────────────────────────────────

def simulate_environment() -> dict:
    """Returns a randomised environment snapshot (temperature + real clock hour)."""
    return {
        "temperature": round(random.uniform(20.0, 40.0), 1),
        "hour":        datetime.now().hour,
    }
