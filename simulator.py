"""Virtual sensor and embedded-style control logic for the simulator."""
import random

def generate_sensor_reading():
    """Generate a plausible virtual sensor sample."""
    return {
        "soil_moisture": round(random.uniform(12, 75), 1),
        "temperature": round(random.uniform(20, 39), 1),
        "humidity": round(random.uniform(30, 88), 1),
        "tank_level": round(random.uniform(0, 100), 1),
    }

def irrigation_decision(reading, pump_on, start_threshold, stop_threshold, min_tank):
    """Apply threshold control, hysteresis and a low-tank safety interlock."""
    required = ["soil_moisture", "temperature", "humidity", "tank_level"]
    if any(key not in reading for key in required):
        return {"pump_on": False, "message": "Sensor data incomplete. Pump forced OFF."}

    for key in required:
        value = reading[key]
        if not isinstance(value, (int, float)):
            return {"pump_on": False, "message": f"Invalid {key} reading. Pump forced OFF."}

    if not (0 <= reading["soil_moisture"] <= 100 and
            0 <= reading["humidity"] <= 100 and
            0 <= reading["tank_level"] <= 100 and
            -10 <= reading["temperature"] <= 60):
        return {"pump_on": False, "message": "Sensor value out of safe range. Pump forced OFF."}

    if reading["tank_level"] < min_tank:
        return {"pump_on": False, "message": "SAFETY: Tank level is too low. Pump is OFF."}

    if pump_on:
        new_state = reading["soil_moisture"] < stop_threshold
    else:
        new_state = reading["soil_moisture"] < start_threshold

    message = "Pump ON: soil is below the start/stop threshold." if new_state else "Pump OFF: moisture target reached or irrigation not required."
    return {"pump_on": new_state, "message": message}
