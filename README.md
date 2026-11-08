# 🌿 Smart Agriculture — Embedded Systems & Automated Irrigation Simulator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Framework-Streamlit](https://img.shields.io/badge/framework-Streamlit-red.svg)](https://streamlit.io/)
[![Database-SQLite](https://img.shields.io/badge/database-SQLite-green.svg)](https://www.sqlite.org/)
[![Status-Complete](https://img.shields.io/badge/status-Complete%20%26%20Tested-brightgreen.svg)]()

A complete academic and engineering software project modeling an IoT-enabled precision irrigation controller with virtual sensor acquisition, ESP32 12-bit ADC mapping, closed-loop hysteresis actuation, reservoir dry-run safety interlocks, and automated technical report generation.

---

## ⚡ Quick Start (Run in 30 Seconds)

Open PowerShell in this workspace directory:

```powershell
# 1. Activate the pre-configured virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run the application
streamlit run app.py
```

> **PowerShell Execution Policy Tip:** If your system blocks activating scripts, simply run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1
> streamlit run app.py
> ```

Open `http://localhost:8501` in your browser.

---

## 🔑 Evaluator & Demo Access

- Click the **"⚡ Quick Evaluator Access"** tab on the login screen and click **"Sign In as Demo Evaluator"** for immediate 1-click access.
- Or use:
  - **Username:** `demo`
  - **Password:** `agrisense123`
- Or register a new account on the "Register" tab.

---

## 📂 Project Structure

```
Smart_Agriculture_Software_Project/
│
├── app.py                             # Root application entry point (launches AgriSense)
├── requirements.txt                   # Project dependencies (Streamlit, Pandas, Plotly, ReportLab)
├── PROJECT_REPORT.md                  # Comprehensive 12-chapter Academic Project Report
├── .venv/                             # Clean, configured Python 3.10 virtual environment
│
├── AgriSense_Complete_Project/        # Primary Production Showcase Package
│   ├── app.py                         # Full feature Streamlit HMI dashboard
│   ├── database.py                    # SQLite database with PBKDF2 authentication
│   ├── simulator.py                   # 12-bit ADC quantization, dynamic telemetry & hysteresis
│   ├── reports.py                     # ReportLab automated PDF report compiler
│   ├── test_project.py                # Automated 9-test verification suite
│   ├── agrisense.db                   # SQLite database (auto-created & migrated)
│   ├── README.md                      # Detailed subproject documentation
│   └── PROJECT_REPORT.md              # Full project report copy
│
└── Smart_Agriculture_Software_Project/ # Basic standalone prototype version
    ├── app.py                         # Lightweight prototype dashboard
    ├── simulator.py                   # Basic simulation logic
    ├── requirements.txt
    └── README.md
```

---

## 🧪 Running Automated Tests

Run the automated test suite verifying ADC mapping, hysteresis, safety interlocks, database transactions, and PDF generation:

```powershell
cd AgriSense_Complete_Project
..\.venv\Scripts\python.exe -m unittest test_project.py
```

**Expected Result:**
```
Ran 9 tests in 0.31s
OK
```

---

## 🌟 Key Engineering Highlights

1. **Closed-Loop Hysteresis Control:** Dual-threshold algorithm ($M < \text{start}$ turns ON, $M \ge \text{stop}$ turns OFF) preventing relay contact arcing and motor chatter.
2. **Hardware Dry-Run Safety Interlock:** Master hardware override preventing pump activation when the water tank level drops below safety minimum ($< 10\%$).
3. **ESP32 12-Bit SAR ADC Model:** Quantizes $0.0\text{V} - 3.3\text{V}$ into 4096 discrete levels ($0 - 4095$) with live register and voltage display.
4. **Crop Agronomic Profiles:** Pre-configured thresholds for 7 crops: *Tomato, Wheat, Paddy/Rice, Maize, Cotton, Potato, and General Crops*.
5. **Dynamic Physics & Weathering:** Models soil drying, rain tank replenishment, and pump water delivery per cycle.
6. **Fault Injection Bench:** Interactive testing of sensor disconnections (ADC open circuit), VCC shorts, and thermal stress.
7. **Automated PDF & CSV Reports:** Instant download of publication-ready audit reports generated via ReportLab.

---

## 🎓 Academic Notice
This project is an embedded systems software simulation. In your project report and viva voce, clearly describe the sensors, ESP32 microcontroller, and pump as software-simulated components. Refer to [`PROJECT_REPORT.md`](PROJECT_REPORT.md) for full project documentation and viva defense Q&A.
