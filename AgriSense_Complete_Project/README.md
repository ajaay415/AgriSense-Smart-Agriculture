# 🌿 AgriSense: Smart Agriculture & Embedded Irrigation Simulator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Framework-Streamlit](https://img.shields.io/badge/framework-Streamlit-red.svg)](https://streamlit.io/)
[![Database-SQLite](https://img.shields.io/badge/database-SQLite-green.svg)](https://www.sqlite.org/)
[![License-Academic](https://img.shields.io/badge/license-Academic%20Project-brightgreen.svg)]()

> **Domain:** Embedded Systems, IoT, Computational Agro-Informatics  
> **Target Controller Architecture:** Espressif ESP32-WROOM-32 SoC  
> **Status:** Software-based simulation & telemetry verification suite  

---

## 📌 Executive Summary
**AgriSense** is a comprehensive software-based simulator that models an intelligent agricultural irrigation and telemetry system. It emulates physical sensor acquisition (capacitive soil moisture, ambient temperature, relative humidity, ultrasonic reservoir level), converts analog voltages using an ESP32 12-bit SAR ADC model, applies closed-loop hysteresis control, and enforces critical hardware safety interlocks (preventing pump cavitation when reservoir water is depleted).

Every telemetry cycle is persisted in a local SQLite database with PBKDF2 user authentication. Users can monitor live data via interactive Plotly charts, perform fault-injection stress testing, export CSV logs, and compile automated publication-grade PDF technical reports.

---

## 🚀 Quick Start Guide (Windows)

### 1. Prerequisites
- **Python 3.10** or later installed.
- PowerShell or Command Prompt.

### 2. Launching the Application
From this folder (`AgriSense_Complete_Project`):

```powershell
# If virtual environment is in the parent root:
..\.venv\Scripts\Activate.ps1

# Run the Streamlit application
streamlit run app.py
```

If PowerShell execution policy blocks activating the virtual environment, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
..\.venv\Scripts\Activate.ps1
streamlit run app.py
```

### 3. Quick Evaluator Access
When the login screen loads in your browser (`http://localhost:8501`):
- Click on the **"⚡ Quick Evaluator Access"** tab and press **"Sign In as Demo Evaluator"** for instant 1-click access without manual registration.
- Alternatively, use default credentials:
  - **Username:** `demo`
  - **Password:** `agrisense123`
- Or register a new personalized account under the "Register" tab.

---

## 🛠️ Key Capabilities & Features

### 1. Embedded Hysteresis & Closed-Loop Control
- **Two-Point Hysteresis:** Pump triggers **ON** when soil moisture drops below `start_threshold` (e.g., 30%) and remains active until moisture reaches `stop_threshold` (e.g., 60%).
- **Relay Anti-Chatter Protection:** Prevents rapid switching oscillations in the deadband `[start, stop]`, preserving relay contacts and electric pump windings.

### 2. Hardware Safety Interlock
- Continuous reservoir tank level monitoring.
- If reservoir level drops below `min_tank` (e.g., 10%), the controller initiates an immediate hardware-priority safety trip, forcing the pump **OFF** regardless of how dry the soil is.

### 3. ESP32 12-Bit SAR ADC Model
- Quantizes simulated sensor voltages ($0.0\,\text{V} - 3.3\,\text{V}$) into 4096 discrete levels ($0 - 4095$).
- Live display of raw register counts, voltages, and hexadecimal conversions.

### 4. Crop & Environmental Presets
- Configured agronomic thresholds for 7 major crop varieties:
  - *Tomato, Wheat, Paddy/Rice, Maize, Cotton, Potato, and General Horticulture*.
- Dynamic weather models (*Sunny/Heatwave, Monsoon/Rain, Moderate, Arid*) with soil evapotranspiration and rainwater tank replenishment.

### 5. Fault Injection Testbench
- Test edge cases live:
  - **Sensor Disconnection:** Simulates ADC open circuit / wire detachment.
  - **Sensor Short Circuit:** Simulates VCC rail shorting.
  - **Empty Reservoir:** Verifies pump protection under extreme drought.
  - **Thermal Stress:** Ambient overload warnings.

### 6. Automated PDF & CSV Reporting
- One-click generation of professional technical PDF audit reports via **ReportLab**.
- Full CSV export of timestamped telemetry history.

---

## 📂 Project Architecture

```
AgriSense_Complete_Project/
├── app.py                      # Main interactive Streamlit application
├── database.py                 # SQLite database driver (PBKDF2 auth & cycle persistence)
├── simulator.py                # Virtual sensor models, 12-bit ADC mapping & hysteresis logic
├── reports.py                  # ReportLab automated PDF report generator
├── test_project.py             # Automated unit & integration test suite (9 tests)
├── requirements.txt            # Python dependencies
├── PROJECT_REPORT_OUTLINE.md   # Initial outline
└── README.md                   # Complete documentation
```

---

## 🧪 Running Automated Tests

Run the test suite from PowerShell:
```powershell
..\.venv\Scripts\python.exe -m unittest test_project.py
```
Expected output:
```
Ran 9 tests in 0.31s
OK
```

---

## 🎓 Academic & Viva Voce Guidance
- **Software Simulation Scope:** This project is designed as a software-in-the-loop embedded simulator. In exams and project presentations, describe sensors, ESP32 microcontrollers, and relay actuators as simulated models.
- **Viva Defense:** Review the **"Project Report & Viva Guide"** tab inside the web app for detailed answers to top questions on hysteresis, active-low logic, ADC quantization, and safety interlocks.
