"""Virtual Sensor and Embedded Control Logic for AgriSense Simulator.

Demonstrates IoT sensor acquisition, 12-bit ADC mapping, hysteresis-based
irrigation actuation, and safety interlock protection.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, Optional

# Pre-configured agronomic threshold profiles for major crops
CROP_PROFILES: Dict[str, Dict[str, Any]] = {
    "General Crop": {
        "start_threshold": 30.0,
        "stop_threshold": 55.0,
        "min_tank": 10.0,
        "temp_min": 18.0,
        "temp_max": 35.0,
        "description": "Balanced baseline profile suitable for typical mixed-bed horticulture.",
    },
    "Tomato (Solanum lycopersicum)": {
        "start_threshold": 35.0,
        "stop_threshold": 65.0,
        "min_tank": 15.0,
        "temp_min": 20.0,
        "temp_max": 30.0,
        "description": "Requires consistent moisture during flowering and fruiting to prevent blossom end rot.",
    },
    "Wheat (Triticum aestivum)": {
        "start_threshold": 25.0,
        "stop_threshold": 50.0,
        "min_tank": 10.0,
        "temp_min": 15.0,
        "temp_max": 25.0,
        "description": "Drought-hardy cereal crop; sensitive to waterlogging during tillering.",
    },
    "Paddy / Rice (Oryza sativa)": {
        "start_threshold": 55.0,
        "stop_threshold": 85.0,
        "min_tank": 20.0,
        "temp_min": 22.0,
        "temp_max": 34.0,
        "description": "Semi-aquatic cultivation requiring high standing water table and frequent irrigation.",
    },
    "Maize / Corn (Zea mays)": {
        "start_threshold": 30.0,
        "stop_threshold": 60.0,
        "min_tank": 12.0,
        "temp_min": 20.0,
        "temp_max": 32.0,
        "description": "Moderate water requirement; critical demand during silking and tassel emergence.",
    },
    "Cotton (Gossypium)": {
        "start_threshold": 22.0,
        "stop_threshold": 48.0,
        "min_tank": 10.0,
        "temp_min": 24.0,
        "temp_max": 37.0,
        "description": "Deep-rooted, heat-tolerant crop; over-irrigation promotes vegetative excessive growth.",
    },
    "Potato (Solanum tuberosum)": {
        "start_threshold": 38.0,
        "stop_threshold": 70.0,
        "min_tank": 15.0,
        "temp_min": 15.0,
        "temp_max": 24.0,
        "description": "Shallow root system; requires uniform soil moisture for uniform tuber bulking.",
    },
}

# Weather conditions influencing evapotranspiration and sensor drift
WEATHER_CONDITIONS: Dict[str, Dict[str, Any]] = {
    "Moderate / Clear": {
        "temp_range": (24.0, 30.0),
        "humidity_range": (45.0, 65.0),
        "soil_decay": 1.2,
        "tank_delta": 0.0,
    },
    "Sunny / Heatwave": {
        "temp_range": (33.0, 42.0),
        "humidity_range": (20.0, 40.0),
        "soil_decay": 2.8,
        "tank_delta": -0.5,
    },
    "Rainy / Monsoon": {
        "temp_range": (21.0, 26.0),
        "humidity_range": (80.0, 96.0),
        "soil_decay": -4.0,  # Rain naturally wets the soil
        "tank_delta": 6.0,   # Rainwater harvesting replenishes tank
    },
    "Arid / Windy": {
        "temp_range": (30.0, 38.0),
        "humidity_range": (15.0, 32.0),
        "soil_decay": 3.4,
        "tank_delta": -0.8,
    },
}


def calculate_adc_mapping(percentage: float, vref: float = 3.3, bits: int = 12) -> Dict[str, float]:
    """Calculate the simulated ESP32 ADC raw register value and voltage.

    ESP32 ADC has a 12-bit SAR (Successive Approximation Register) converter
    producing values from 0 to 4095.
    Capacitive Soil Moisture Sensors typically output higher voltage when dry
    and lower voltage when wet (inverted), but for direct reading representation:
    Voltage = (percentage / 100.0) * vref
    ADC Count = round((percentage / 100.0) * (2**bits - 1))
    """
    max_count = (1 << bits) - 1
    pct = max(0.0, min(100.0, float(percentage)))
    adc_count = int(round((pct / 100.0) * max_count))
    voltage = round((pct / 100.0) * vref, 3)
    return {
        "adc_count": adc_count,
        "voltage": voltage,
        "vref": vref,
        "resolution_bits": bits,
    }


def generate_sensor_reading(
    prev_reading: Optional[Dict[str, Any]] = None,
    weather: str = "Moderate / Clear",
    pump_active: bool = False,
    fault_injection: str = "Normal Operation",
) -> Dict[str, Any]:
    """Generate realistic virtual sensor telemetry.

    Supports continuous dynamic modeling:
    - Pump actuation increases moisture and depletes the water tank.
    - Evapotranspiration dries the soil based on current weather.
    - Rain replenishes the tank and hydrates the soil.
    - Fault injection models physical sensor failure scenarios.
    """
    # 1. Handle Fault Injection Cases for Testing
    if fault_injection == "Sensor Disconnected":
        return {
            "soil_moisture": None,
            "temperature": None,
            "humidity": None,
            "tank_level": 75.0,
            "fault_active": True,
            "fault_type": "ADC Open Circuit / Wire Disconnected",
        }
    if fault_injection == "Sensor Short Circuit":
        return {
            "soil_moisture": 135.0,  # Out-of-bounds
            "temperature": 85.0,
            "humidity": 120.0,
            "tank_level": 70.0,
            "fault_active": True,
            "fault_type": "Sensor VCC Short to ADC Rail",
        }
    if fault_injection == "Empty Water Tank":
        return {
            "soil_moisture": 18.0,
            "temperature": 32.0,
            "humidity": 40.0,
            "tank_level": 3.0,  # Below safety threshold
            "fault_active": True,
            "fault_type": "Tank Depleted Below Safety Minimum",
        }
    if fault_injection == "Thermal Warning":
        return {
            "soil_moisture": 25.0,
            "temperature": 49.5,
            "humidity": 20.0,
            "tank_level": 60.0,
            "fault_active": True,
            "fault_type": "High Ambient Thermal Stress",
        }

    weather_cfg = WEATHER_CONDITIONS.get(weather, WEATHER_CONDITIONS["Moderate / Clear"])
    temp_min, temp_max = weather_cfg["temp_range"]
    hum_min, hum_max = weather_cfg["humidity_range"]

    if prev_reading is not None and isinstance(prev_reading.get("soil_moisture"), (int, float)):
        # Continuous Dynamic Simulation based on physical state
        current_soil = float(prev_reading["soil_moisture"])
        current_tank = float(prev_reading.get("tank_level", 75.0))

        if pump_active:
            # Active irrigation delivery
            soil_delta = random.uniform(3.5, 6.0)
            tank_delta = -random.uniform(2.5, 4.0)
        else:
            # Natural drying / weathering
            soil_delta = -weather_cfg["soil_decay"] + random.uniform(-0.3, 0.3)
            tank_delta = weather_cfg["tank_delta"] + random.uniform(-0.2, 0.2)

        soil = max(5.0, min(95.0, current_soil + soil_delta))
        tank = max(0.0, min(100.0, current_tank + tank_delta))
        temp = round(random.uniform(temp_min, temp_max), 1)
        hum = round(random.uniform(hum_min, hum_max), 1)
    else:
        # Seed fresh realistic state
        soil = round(random.uniform(20.0, 50.0), 1)
        temp = round(random.uniform(temp_min, temp_max), 1)
        hum = round(random.uniform(hum_min, hum_max), 1)
        tank = round(random.uniform(60.0, 95.0), 1)

    # 12-bit ADC mapping for educational inspection
    soil_adc = calculate_adc_mapping(soil)

    return {
        "soil_moisture": round(soil, 1),
        "temperature": round(temp, 1),
        "humidity": round(hum, 1),
        "tank_level": round(tank, 1),
        "adc_soil_count": soil_adc["adc_count"],
        "adc_soil_voltage": soil_adc["voltage"],
        "fault_active": False,
        "fault_type": "None (Healthy)",
    }


def irrigation_decision(
    reading: Dict[str, Any],
    pump_on: bool,
    start_threshold: float,
    stop_threshold: float,
    min_tank: float,
) -> Dict[str, Any]:
    """Execute embedded-style control algorithm.

    Applies:
    1. Input validation & sanity checks
    2. Range checking (prevents sensor glitches from damaging hardware)
    3. Low-water tank safety interlock (prevents pump dry-running)
    4. Two-point hysteresis control to prevent rapid relay chattering
    """
    required_keys = ("soil_moisture", "temperature", "humidity", "tank_level")

    # 1. Validation check
    for key in required_keys:
        if key not in reading or reading[key] is None:
            return {
                "pump_on": False,
                "status": "FAILSAFE",
                "message": f"CRITICAL: Missing or invalid '{key}' data. Pump forced OFF.",
                "safety_triggered": True,
                "relay_signal": "HIGH (De-energized)",
            }
        try:
            float(reading[key])
        except (ValueError, TypeError):
            return {
                "pump_on": False,
                "status": "FAILSAFE",
                "message": f"CRITICAL: Non-numeric reading in '{key}'. Pump forced OFF.",
                "safety_triggered": True,
                "relay_signal": "HIGH (De-energized)",
            }

    soil = float(reading["soil_moisture"])
    temp = float(reading["temperature"])
    hum = float(reading["humidity"])
    tank = float(reading["tank_level"])

    # 2. Sensor physical range bounds
    if not (0.0 <= soil <= 100.0 and 0.0 <= hum <= 100.0 and 0.0 <= tank <= 100.0 and -10.0 <= temp <= 60.0):
        return {
            "pump_on": False,
            "status": "SENSOR_FAULT",
            "message": "SAFETY TRIPPED: Sensor value outside operational envelope. Pump locked OFF.",
            "safety_triggered": True,
            "relay_signal": "HIGH (De-energized)",
        }

    # 3. Low-tank dry-run safety interlock
    if tank < min_tank:
        return {
            "pump_on": False,
            "status": "INTERLOCK_ENGAGED",
            "message": f"SAFETY INTERLOCK: Reservoir tank ({tank:.1f}%) is below minimum threshold ({min_tank:.1f}%). Pump disabled to prevent dry-running.",
            "safety_triggered": True,
            "relay_signal": "HIGH (De-energized)",
        }

    # 4. Hysteresis control logic
    if pump_on:
        # Keep pumping until stop_threshold is satisfied
        if soil >= stop_threshold:
            new_pump_state = False
            msg = f"Pump OFF: Target soil moisture ({stop_threshold:.1f}%) reached. Soil adequately hydrated."
            status = "IRRIGATION_COMPLETE"
        else:
            new_pump_state = True
            msg = f"Pump ON: Moisture is {soil:.1f}% (target: {stop_threshold:.1f}%). Continuing irrigation."
            status = "IRRIGATING"
    else:
        # Only start if soil drops below start_threshold
        if soil < start_threshold:
            new_pump_state = True
            msg = f"Pump ON: Soil moisture ({soil:.1f}%) fell below activation threshold ({start_threshold:.1f}%)."
            status = "IRRIGATING"
        else:
            new_pump_state = False
            msg = f"Pump OFF: Soil moisture ({soil:.1f}%) is within optimal band (hysteresis window [{start_threshold:.1f}%, {stop_threshold:.1f}%])."
            status = "IDLE_MONITORING"

    relay = "LOW (Energized)" if new_pump_state else "HIGH (De-energized)"
    return {
        "pump_on": new_pump_state,
        "status": status,
        "message": msg,
        "safety_triggered": False,
        "relay_signal": relay,
    }


def recommendation(
    reading: Dict[str, Any],
    start: float,
    stop: float,
    min_tank: float,
    crop_name: str = "General Crop",
) -> str:
    """Generate agronomic advisory recommendations."""
    if not isinstance(reading.get("tank_level"), (int, float)):
        return "Diagnostic Advisory: Check wiring harness and ADC connections to restore telemetry."

    tank = float(reading["tank_level"])
    soil = float(reading["soil_moisture"])
    temp = float(reading["temperature"])

    if tank < min_tank:
        return f"CRITICAL ACTION: Replenish the irrigation water reservoir immediately. The controller has halted pump actuation to protect the motor from cavitation."
    if soil < start:
        return f"Agronomic Alert: {crop_name} root zone moisture is critically low. Active watering underway to maintain transpiration."
    if soil >= stop:
        return f"Optimal Status: Moisture target reached. Soil root zone exhibits good water potential. No watering required."
    if temp >= 38.0:
        return f"Heat Stress Advisory: High ambient temperature detected ({temp:.1f} °C). Monitor for rapid evapotranspiration and leaf wilting."
    return f"Stable: Environmental and soil metrics for {crop_name} remain within configured setpoints."
