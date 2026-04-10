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
    def __init__(self, temperature, hour, is_occupied):
        self.temperature = temperature
        self.hour = hour
        self.is_occupied = is_occupied

    @property
    def is_night(self):
        return self.hour >= 22 or self.hour < 6

    @property
    def time_label(self):
        return "night" if self.is_night else "day"

def simulate_environment():
    temp = round(random.uniform(20.0, 42.0), 1)
    hour = random.randint(0, 23)

    # Occupancy simulation
    if 8 <= hour <= 22:
        is_occupied = random.random() < 0.4
    else:
        is_occupied = random.random() < 0.6

    return Environment(temperature=temp, hour=hour, is_occupied=is_occupied)

class TemperatureAgent:
    def decide(self, env):
        t = env.temperature
        if t < 20:
            return FanSpeed.OFF, f"{t}C is cool (<20), fan OFF"
        elif t < 24:
            return FanSpeed.LOW, f"{t}C is comfortable (20-24), fan LOW"
        elif t < 28:
            return FanSpeed.MEDIUM, f"{t}C is warm (24-28), fan MEDIUM"
        else:
            return FanSpeed.HIGH, f"{t}C is hot (>=28), fan HIGH"

class UserPreferenceAgent:
    def decide(self, env):
        t = env.temperature

        if env.is_night:
            if t >= 32:
                return FanSpeed.MEDIUM, "Night but hot - allow MEDIUM"
            elif t >= 26:
                return FanSpeed.LOW, "Night moderate - prefer LOW"
            else:
                return FanSpeed.OFF, "Night cool - turn OFF"
        
        return None, "Daytime - no preference"

class EnergyOptimizationAgent:
    def decide(self, current, env):
        """
        Context-aware energy optimization:
        - Preserve comfort at high temperatures
        - Reduce speed only when safe
        - Use occupancy + temperature thresholds
        """

        t = env.temperature

        # Rule 1: If no one is present → turn OFF
        if not env.is_occupied:
            return FanSpeed.OFF, "Room unoccupied → fan OFF"

        # Rule 2: VERY HOT → do NOT reduce (comfort priority)
        if t >= 36:
            return current, "Very hot → maintaining current speed for comfort"

        # Rule 3: HOT but not extreme → allow HIGH, avoid aggressive downgrade
        if 32 <= t < 36:
            if current == FanSpeed.HIGH:
                return FanSpeed.HIGH, "Hot → keeping HIGH"
            return current, "Hot → no energy reduction"

        # Rule 4: MODERATE → allow slight optimization
        if 28 <= t < 32:
            if current == FanSpeed.HIGH:
                return FanSpeed.MEDIUM, "Moderate → reduce HIGH to MEDIUM"
            return current, "Moderate → no further reduction"

        # Rule 5: COMFORTABLE → optimize more
        if 24 <= t < 28:
            if current == FanSpeed.MEDIUM:
                return FanSpeed.LOW, "Comfortable → reduce MEDIUM to LOW"
            if current == FanSpeed.HIGH:
                return FanSpeed.MEDIUM, "Comfortable → reduce HIGH to MEDIUM"
            return current, "Comfortable → minimal cooling needed"

        # Rule 6: COOL → turn OFF
        if t < 24:
            return FanSpeed.OFF, "Cool → turning fan OFF"

        return current, "No change"

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

        final, energy_reason = self.energy_agent.decide(combined, env)

        return {
            "final_speed": str(final),
            "environment": {
                "temperature": env.temperature,
                "hour": env.hour,
                "time_of_day": env.time_label,
                "occupied": env.is_occupied,
            },
            "agent_log": [
                {"agent": "TemperatureAgent", "vote": str(temp_vote), "reason": temp_reason},
                {"agent": "UserPreferenceAgent", "vote": str(pref_vote) if pref_vote else "NONE", "reason": pref_reason},
                {"agent": "EnergyOptimizationAgent", "vote": str(final), "reason": energy_reason},
            ]
        }

coordinator = CoordinatorAgent()