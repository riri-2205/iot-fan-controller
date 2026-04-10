import random
from enum import IntEnum

class FanSpeed(IntEnum):
    OFF = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    def __str__(self):
        return self.name

class Environment:
    def __init__(self, temperature, hour):
        self.temperature = temperature
        self.hour = hour
    @property
    def is_night(self):
        return self.hour >= 22 or self.hour < 6
    @property
    def time_label(self):
        return "night" if self.is_night else "day"

def simulate_environment():
    temp = round(random.uniform(20.0, 42.0), 1)
    hour = random.randint(0, 23)
    return Environment(temperature=temp, hour=hour)

class TemperatureAgent:
    def decide(self, env):
        t = env.temperature
        if t < 25:
            return FanSpeed.OFF, f"{t}C is cool, fan OFF"
        elif t < 30:
            return FanSpeed.LOW, f"{t}C is mild, fan LOW"
        elif t < 35:
            return FanSpeed.MEDIUM, f"{t}C is warm, fan MEDIUM"
        else:
            return FanSpeed.HIGH, f"{t}C is hot, fan HIGH"

class UserPreferenceAgent:
    def decide(self, env):
        if env.is_night:
            return FanSpeed.LOW, "Night time - keep it quiet, prefer LOW"
        return None, "Daytime - no preference"

class EnergyOptimizationAgent:
    def decide(self, current):
        if current == FanSpeed.HIGH:
            return FanSpeed.MEDIUM, "Saving energy - reduced HIGH to MEDIUM"
        return current, "No energy change needed"

class CoordinatorAgent:
    def __init__(self):
        self.temp_agent = TemperatureAgent()
        self.pref_agent = UserPreferenceAgent()
        self.energy_agent = EnergyOptimizationAgent()

    def decide(self, env):
        temp_vote, temp_reason = self.temp_agent.decide(env)
        pref_vote, pref_reason = self.pref_agent.decide(env)

        if pref_vote is not None:
            combined = min(temp_vote, pref_vote)
        else:
            combined = temp_vote

        final, energy_reason = self.energy_agent.decide(combined)

        return {
            "final_speed": str(final),
            "environment": {
                "temperature": env.temperature,
                "hour": env.hour,
                "time_of_day": env.time_label,
            },
            "agent_log": [
                {"agent": "TemperatureAgent", "vote": str(temp_vote), "reason": temp_reason},
                {"agent": "UserPreferenceAgent", "vote": str(pref_vote) if pref_vote else "NONE", "reason": pref_reason},
                {"agent": "EnergyOptimizationAgent", "vote": str(final), "reason": energy_reason},
            ]
        }

coordinator = CoordinatorAgent()