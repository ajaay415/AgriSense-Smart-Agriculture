"""Automated Test Suite for AgriSense Embedded Agriculture Simulator.

Covers:
- 12-bit ADC resolution & quantization mapping
- Sensor generation & dynamic physical modeling
- Hysteresis control logic & deadband verification
- Low-tank safety interlock priority
- Failsafe handling of sensor faults and out-of-range values
- SQLite database transactions, PBKDF2 authentication, and telemetry logging
- ReportLab PDF generation
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path
PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd
from database import (
    clear_cycles,
    create_user,
    get_cycles,
    get_statistics,
    init_db,
    save_cycle,
    verify_user,
)
from reports import make_pdf
from simulator import (
    CROP_PROFILES,
    WEATHER_CONDITIONS,
    calculate_adc_mapping,
    generate_sensor_reading,
    irrigation_decision,
    recommendation,
)


class TestSimulatorLogic(unittest.TestCase):
    """Test telemetry generation, ADC quantization, and control decision algorithms."""

    def test_adc_quantization(self):
        """Verify ESP32 12-bit ADC mapping logic."""
        # Minimum (0%)
        zero = calculate_adc_mapping(0.0)
        self.assertEqual(zero["adc_count"], 0)
        self.assertEqual(zero["voltage"], 0.0)

        # Maximum (100%)
        full = calculate_adc_mapping(100.0)
        self.assertEqual(full["adc_count"], 4095)
        self.assertAlmostEqual(full["voltage"], 3.3, places=2)

        # Midpoint (50%)
        mid = calculate_adc_mapping(50.0)
        self.assertIn(mid["adc_count"], [2047, 2048])
        self.assertAlmostEqual(mid["voltage"], 1.65, places=2)

    def test_dynamic_telemetry_generation(self):
        """Verify normal telemetry generation within physical bounds."""
        rd = generate_sensor_reading(weather="Moderate / Clear")
        self.assertIn("soil_moisture", rd)
        self.assertIn("temperature", rd)
        self.assertIn("humidity", rd)
        self.assertIn("tank_level", rd)
        self.assertTrue(0.0 <= rd["soil_moisture"] <= 100.0)
        self.assertTrue(0.0 <= rd["tank_level"] <= 100.0)
        self.assertTrue(-10.0 <= rd["temperature"] <= 60.0)

    def test_pump_actuation_dynamics(self):
        """Verify that running the pump increases soil moisture and decreases tank."""
        initial_reading = {
            "soil_moisture": 20.0,
            "temperature": 25.0,
            "humidity": 50.0,
            "tank_level": 80.0,
        }
        next_rd = generate_sensor_reading(
            prev_reading=initial_reading,
            pump_active=True,
            weather="Moderate / Clear",
        )
        self.assertGreater(next_rd["soil_moisture"], initial_reading["soil_moisture"])
        self.assertLess(next_rd["tank_level"], initial_reading["tank_level"])

    def test_hysteresis_control_cycle(self):
        """Verify two-point hysteresis logic prevents relay chattering."""
        start_th = 30.0
        stop_th = 60.0
        min_tank = 10.0

        # Case 1: Dry soil, currently OFF -> Turns ON
        dry = {"soil_moisture": 20.0, "temperature": 28.0, "humidity": 45.0, "tank_level": 70.0}
        dec = irrigation_decision(dry, pump_on=False, start_threshold=start_th, stop_threshold=stop_th, min_tank=min_tank)
        self.assertTrue(dec["pump_on"])

        # Case 2: In hysteresis deadband (45%), currently ON -> Stays ON
        deadband = {"soil_moisture": 45.0, "temperature": 28.0, "humidity": 45.0, "tank_level": 70.0}
        dec = irrigation_decision(deadband, pump_on=True, start_threshold=start_th, stop_threshold=stop_th, min_tank=min_tank)
        self.assertTrue(dec["pump_on"], "Pump should remain ON in deadband until stop threshold is achieved.")

        # Case 3: Target reached (65%), currently ON -> Turns OFF
        wet = {"soil_moisture": 65.0, "temperature": 28.0, "humidity": 45.0, "tank_level": 70.0}
        dec = irrigation_decision(wet, pump_on=True, start_threshold=start_th, stop_threshold=stop_th, min_tank=min_tank)
        self.assertFalse(dec["pump_on"], "Pump must turn OFF when moisture meets or exceeds stop threshold.")

        # Case 4: In hysteresis deadband (45%), currently OFF -> Stays OFF
        dec = irrigation_decision(deadband, pump_on=False, start_threshold=start_th, stop_threshold=stop_th, min_tank=min_tank)
        self.assertFalse(dec["pump_on"], "Pump should remain OFF in deadband until start threshold is reached.")

    def test_safety_interlock_dry_tank(self):
        """Verify that empty reservoir forces pump OFF even with bone-dry soil."""
        bone_dry = {"soil_moisture": 5.0, "temperature": 32.0, "humidity": 30.0, "tank_level": 4.0}
        dec = irrigation_decision(
            bone_dry,
            pump_on=True,
            start_threshold=30.0,
            stop_threshold=60.0,
            min_tank=10.0,
        )
        self.assertFalse(dec["pump_on"])
        self.assertTrue(dec["safety_triggered"])
        self.assertIn("SAFETY INTERLOCK", dec["message"])

    def test_sensor_fault_injection(self):
        """Verify failsafe behavior when sensors disconnect or short."""
        # Open circuit (None)
        fault_open = generate_sensor_reading(fault_injection="Sensor Disconnected")
        dec = irrigation_decision(fault_open, pump_on=True, start_threshold=30.0, stop_threshold=60.0, min_tank=10.0)
        self.assertFalse(dec["pump_on"])
        self.assertTrue(dec["safety_triggered"])

        # Short circuit (135% moisture)
        fault_short = generate_sensor_reading(fault_injection="Sensor Short Circuit")
        dec = irrigation_decision(fault_short, pump_on=True, start_threshold=30.0, stop_threshold=60.0, min_tank=10.0)
        self.assertFalse(dec["pump_on"])
        self.assertTrue(dec["safety_triggered"])


class TestDatabaseAndReports(unittest.TestCase):
    """Test database operations, user management, and PDF report creation."""

    def setUp(self):
        init_db()

    def test_user_creation_and_auth(self):
        """Verify PBKDF2 authentication and uniqueness constraints."""
        username = f"testuser_{os.urandom(4).hex()}"
        ok, msg = create_user(username, "secret123")
        self.assertTrue(ok)

        # Authenticate with correct password
        user = verify_user(username, "secret123")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], username)

        # Reject incorrect password
        bad_user = verify_user(username, "wrongpassword")
        self.assertIsNone(bad_user)

        # Reject duplicate username
        dup_ok, _ = create_user(username, "secret123")
        self.assertFalse(dup_ok)

    def test_cycle_logging_and_stats(self):
        """Verify telemetry logging and aggregate metrics calculation."""
        username = f"metric_user_{os.urandom(4).hex()}"
        create_user(username, "password123")
        user = verify_user(username, "password123")
        uid = user["id"]

        clear_cycles(uid)

        # Log 2 cycles
        rd1 = {"soil_moisture": 22.0, "temperature": 28.0, "humidity": 50.0, "tank_level": 80.0, "adc_soil_count": 901, "adc_soil_voltage": 0.72}
        save_cycle(uid, rd1, pump_on=True, message="Pump ON", input_mode="Dynamic Virtual Sensors", crop_type="Tomato", water_used_liters=2.5)

        rd2 = {"soil_moisture": 45.0, "temperature": 27.5, "humidity": 55.0, "tank_level": 77.5, "adc_soil_count": 1845, "adc_soil_voltage": 1.48}
        save_cycle(uid, rd2, pump_on=False, message="Pump OFF", input_mode="Dynamic Virtual Sensors", crop_type="Tomato", water_used_liters=0.0)

        cycles = get_cycles(uid)
        self.assertEqual(len(cycles), 2)

        stats = get_statistics(uid)
        self.assertEqual(stats["total_cycles"], 2)
        self.assertEqual(stats["pump_on_cycles"], 1)
        self.assertEqual(stats["total_water"], 2.5)

        clear_cycles(uid)
        self.assertEqual(len(get_cycles(uid)), 0)

    def test_pdf_generation(self):
        """Verify that ReportLab produces valid binary PDF data."""
        data = [
            {
                "created_at": "2026-11-08 12:00:00",
                "crop_type": "Tomato",
                "soil_moisture": 25.0,
                "temperature": 29.0,
                "humidity": 50.0,
                "tank_level": 80.0,
                "pump_state": 1,
                "message": "Pumping",
            }
        ]
        df = pd.DataFrame(data)
        pdf = make_pdf("test_evaluator", df, {"total_cycles": 1, "pump_on_cycles": 1, "total_water": 2.5, "avg_moisture": 25.0})
        self.assertTrue(isinstance(pdf, bytes))
        self.assertTrue(pdf.startswith(b"%PDF"), "Output must be valid PDF stream starting with %PDF magic bytes.")


if __name__ == "__main__":
    unittest.main()
