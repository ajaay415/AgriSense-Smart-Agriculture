"""AgriSense: Smart Agriculture Monitoring and Automated Irrigation Simulator.

A complete software-based embedded systems project built with Streamlit, SQLite,
Plotly, and ReportLab. Demonstrates IoT sensor telemetry, 12-bit ADC conversion,
closed-loop hysteresis irrigation, low-water safety interlocks, and automated reporting.
"""

from __future__ import annotations

import time
from typing import Any, Dict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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

# Page configuration
st.set_page_config(
    page_title="AgriSense | Smart Agriculture Simulator",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize SQLite database
init_db()

# Custom CSS for modern styling
st.markdown(
    """
    <style>
    /* Theme Accents */
    .stApp {
        background: linear-gradient(145deg, #0b1a15 0%, #112821 50%, #0d1e18 100%);
        color: #e8f5e9;
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #081612 !important;
        border-right: 1px solid #1a382e;
    }
    div[data-testid="stMetric"] {
        background: rgba(22, 53, 42, 0.7);
        border: 1px solid #285a47;
        padding: 14px 18px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    div[data-testid="stMetricValue"] {
        color: #52b788 !important;
        font-weight: 700;
    }
    .status-card {
        padding: 16px 20px;
        border-radius: 10px;
        margin-bottom: 14px;
        font-weight: 500;
    }
    .status-irrigating {
        background-color: rgba(46, 125, 50, 0.25);
        border: 1px solid #4caf50;
        color: #a5d6a7;
    }
    .status-idle {
        background-color: rgba(33, 150, 243, 0.15);
        border: 1px solid #2196f3;
        color: #90caf9;
    }
    .status-safety {
        background-color: rgba(211, 47, 47, 0.25);
        border: 1px solid #f44336;
        color: #ef9a9a;
    }
    .viva-card {
        background: rgba(18, 44, 35, 0.6);
        border-left: 4px solid #52b788;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_auth_modal():
    """Render Login, Registration, and Instant Demo Access."""
    st.markdown("<h1 style='text-align: center; color: #52b788;'>🌿 AgriSense</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align: center; color: #a3c4b8;'>Software-Based Smart Agriculture & Embedded Irrigation Simulator</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register, tab_demo = st.tabs(["🔑 Sign In", "📝 Register", "⚡ Quick Evaluator Access"])

        with tab_login:
            with st.form("form_login"):
                uname = st.text_input("Username", key="login_u")
                passwd = st.text_input("Password", type="password", key="login_p")
                submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)
            if submit:
                user = verify_user(uname.strip(), passwd)
                if user:
                    st.session_state.user = user
                    st.success(f"Welcome back, {user['username']}!")
                    time.sleep(0.3)
                    st.rerun()
                else:
                    st.error("Invalid credentials. Try the 'Quick Evaluator Access' tab for instant login.")

        with tab_register:
            with st.form("form_register"):
                reg_u = st.text_input("New Username", key="reg_u")
                reg_p = st.text_input("Password (min 6 chars)", type="password", key="reg_p")
                reg_p2 = st.text_input("Confirm Password", type="password", key="reg_p2")
                submit_reg = st.form_submit_button("Create Account", use_container_width=True)
            if submit_reg:
                if reg_p != reg_p2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = create_user(reg_u, reg_p)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        with tab_demo:
            st.info("For viva, project demonstration, or grading, enter instantly with the pre-seeded account:")
            if st.button("🚀 Sign In as Demo Evaluator", type="primary", use_container_width=True):
                user = verify_user("demo", "agrisense123")
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    create_user("demo", "agrisense123")
                    st.session_state.user = verify_user("demo", "agrisense123")
                    st.rerun()


# Guard authentication
if "user" not in st.session_state:
    render_auth_modal()
    st.stop()

# Active logged-in user
current_user = st.session_state.user
uid = current_user["id"]

# Initialize session state flags
if "last_reading" not in st.session_state:
    prior = get_cycles(uid, 1)
    if prior:
        p = prior[0]
        st.session_state.last_reading = {
            "soil_moisture": p["soil_moisture"],
            "temperature": p["temperature"],
            "humidity": p["humidity"],
            "tank_level": p["tank_level"],
            "adc_soil_count": p.get("adc_count", 0),
            "adc_soil_voltage": p.get("voltage", 0.0),
        }
        st.session_state.pump_state = bool(p["pump_state"])
        st.session_state.last_message = p["message"]
    else:
        st.session_state.last_reading = None
        st.session_state.pump_state = False
        st.session_state.last_message = "Simulator initialized. Ready for execution."

if "auto_run" not in st.session_state:
    st.session_state.auto_run = False


# Sidebar Configuration
with st.sidebar:
    st.markdown("### 🌿 AgriSense Simulator")
    st.caption(f"Signed in as: **{current_user['username']}**")
    if st.button("🚪 Sign Out", use_container_width=True):
        del st.session_state.user
        st.rerun()

    st.divider()
    page = st.radio(
        "Navigation",
        [
            "📊 Live Dashboard & Control",
            "📈 Analytics & Historical Trends",
            "🔌 ESP32 Embedded Architecture",
            "🧪 Fault Injection Testbench",
            "📑 PDF Reports & Data Export",
        ],
    )

    st.divider()
    st.subheader("🌾 Crop & Field Preset")
    selected_crop = st.selectbox("Select Crop Type", list(CROP_PROFILES.keys()), index=0)
    crop_info = CROP_PROFILES[selected_crop]
    st.caption(f"*{crop_info['description']}*")

    # Threshold Controls (pre-loaded from crop preset)
    st.subheader("⚙️ Control Thresholds")
    use_custom_thresholds = st.checkbox("Customize Thresholds", value=False)
    if use_custom_thresholds:
        start_th = st.slider("Pump ON Below Soil Moisture (%)", 5.0, 70.0, crop_info["start_threshold"], step=1.0)
        stop_th = st.slider("Pump OFF At Soil Moisture (%)", start_th + 1.0, 95.0, crop_info["stop_threshold"], step=1.0)
        min_tank = st.slider("Safety Minimum Tank Level (%)", 0.0, 40.0, crop_info["min_tank"], step=1.0)
    else:
        start_th = crop_info["start_threshold"]
        stop_th = crop_info["stop_threshold"]
        min_tank = crop_info["min_tank"]
        st.info(f"Target Band: **{start_th:.0f}%** to **{stop_th:.0f}%** | Min Tank: **{min_tank:.0f}%**")

    st.caption("ℹ️ Hysteresis prevents rapid on/off switching (relay chatter).")


# =====================================================================
# PAGE 1: LIVE DASHBOARD & CONTROL
# =====================================================================
if page == "📊 Live Dashboard & Control":
    st.title("📊 Live Telemetry & Irrigation Controller")
    st.markdown("Virtual Embedded ESP32 Controller with Closed-Loop Hysteresis Actuation")

    # Control Bar
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1.5, 1.5, 1.5])

    with ctrl_col1:
        input_mode = st.radio("Telemetry Mode", ["Dynamic Virtual Sensors", "Manual Controlled Input"], horizontal=True)

    with ctrl_col2:
        if input_mode == "Dynamic Virtual Sensors":
            weather = st.selectbox("Simulated Ambient Environment", list(WEATHER_CONDITIONS.keys()), index=0)
        else:
            weather = "Moderate / Clear"

    with ctrl_col3:
        st.write("Virtual Actuator Flow")
        pump_flow = st.number_input("Pump Delivery (L/cycle)", min_value=0.5, max_value=20.0, value=2.5, step=0.5)

    # Manual Sliders if selected
    if input_mode == "Manual Controlled Input":
        st.markdown("##### 🎛️ Manual Sensor Calibration Sliders")
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        m_soil = m_c1.slider("Manual Soil Moisture (%)", 0.0, 100.0, 22.0, step=0.5)
        m_temp = m_c2.slider("Manual Temperature (°C)", -5.0, 55.0, 29.5, step=0.5)
        m_hum = m_c3.slider("Manual Humidity (%)", 0.0, 100.0, 52.0, step=0.5)
        m_tank = m_c4.slider("Manual Tank Level (%)", 0.0, 100.0, 85.0, step=0.5)

    # Action Buttons
    b_col1, b_col2, b_col3, b_col4 = st.columns([1.2, 1.2, 1.2, 1.4])
    run_one = b_col1.button("▶ Run 1 Cycle", type="primary", use_container_width=True)
    run_batch = b_col2.button("🧪 Run 5 Cycles", use_container_width=True)
    run_twenty = b_col3.button("⚡ Fast Sim (20 Cycles)", use_container_width=True)

    auto_toggle = b_col4.checkbox("🔄 Auto-Run Live (2s Interval)", value=st.session_state.auto_run)
    st.session_state.auto_run = auto_toggle

    # Cycle Execution Processing
    cycles_to_run = 0
    if run_one:
        cycles_to_run = 1
    elif run_batch:
        cycles_to_run = 5
    elif run_twenty:
        cycles_to_run = 20
    elif st.session_state.auto_run:
        cycles_to_run = 1

    if cycles_to_run > 0:
        current_pump = st.session_state.get("pump_state", False)
        last_rd = st.session_state.get("last_reading", None)

        for _ in range(cycles_to_run):
            if input_mode == "Dynamic Virtual Sensors":
                telemetry = generate_sensor_reading(
                    prev_reading=last_rd,
                    weather=weather,
                    pump_active=current_pump,
                )
            else:
                adc_data = calculate_adc_mapping(m_soil)
                telemetry = {
                    "soil_moisture": m_soil,
                    "temperature": m_temp,
                    "humidity": m_hum,
                    "tank_level": m_tank,
                    "adc_soil_count": adc_data["adc_count"],
                    "adc_soil_voltage": adc_data["voltage"],
                    "fault_active": False,
                }

            decision = irrigation_decision(
                telemetry,
                pump_on=current_pump,
                start_threshold=start_th,
                stop_threshold=stop_th,
                min_tank=min_tank,
            )
            current_pump = decision["pump_on"]

            # Compute estimated water delivered this cycle
            water_delivered = pump_flow if current_pump else 0.0

            # Save to SQLite database
            save_cycle(
                user_id=uid,
                reading=telemetry,
                pump_on=current_pump,
                message=decision["message"],
                input_mode=input_mode,
                crop_type=selected_crop,
                water_used_liters=water_delivered,
            )

            last_rd = telemetry
            st.session_state.last_reading = telemetry
            st.session_state.pump_state = current_pump
            st.session_state.last_message = decision["message"]
            st.session_state.last_decision = decision

        if st.session_state.auto_run:
            time.sleep(1.5)
            st.rerun()
        else:
            st.rerun()

    # Display Metrics & Actuator State
    st.divider()
    latest = st.session_state.get("last_reading")
    pump_active = st.session_state.get("pump_state", False)

    if latest:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric(
            "🌱 Soil Moisture",
            f"{latest['soil_moisture']:.1f}%",
            delta=f"ADC: {latest.get('adc_soil_count', 0)} ({latest.get('adc_soil_voltage', 0.0):.2f}V)",
        )
        m2.metric(
            "🌡️ Temperature",
            f"{latest['temperature']:.1f} °C",
            delta="Optimal" if crop_info["temp_min"] <= latest["temperature"] <= crop_info["temp_max"] else "Stress",
        )
        m3.metric("💧 Humidity", f"{latest['humidity']:.1f}%")
        m4.metric(
            "🪣 Reservoir Tank",
            f"{latest['tank_level']:.1f}%",
            delta="OK" if latest["tank_level"] >= min_tank else "CRITICAL LOW",
            delta_color="normal" if latest["tank_level"] >= min_tank else "inverse",
        )
        pump_label = "PUMPING (ON)" if pump_active else "STANDBY (OFF)"
        m5.metric("⚡ Virtual Pump", pump_label, delta="Relay Active" if pump_active else "Relay Open")

        # Actuator Banner & Recommendations
        msg = st.session_state.get("last_message", "")
        if "SAFETY" in msg or "CRITICAL" in msg:
            st.error(f"🚨 **SAFETY INTERLOCK ENGAGED:** {msg}")
        elif pump_active:
            st.success(f"💧 **IRRIGATION ACTIVE:** {msg}")
        else:
            st.info(f"🌿 **SYSTEM MONITORING:** {msg}")

        # Agronomic recommendation
        st.markdown(
            f"**Agronomic Advisory ({selected_crop}):** "
            + recommendation(latest, start_th, stop_th, min_tank, selected_crop)
        )
    else:
        st.info("No telemetry recorded yet. Click '▶ Run 1 Cycle' or '🧪 Run 5 Cycles' to begin simulation.")

    # High-level Statistics Row
    stats = get_statistics(uid)
    if stats["total_cycles"] > 0:
        st.markdown("---")
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Total Cycles Logged", stats["total_cycles"])
        s2.metric("Irrigation Cycles", stats["pump_on_cycles"])
        s3.metric("Irrigation Duty Cycle", f"{stats['irrigation_ratio']}%")
        s4.metric("Est. Water Delivered", f"{stats['total_water']:.1f} L")
        s5.metric("Avg Soil Moisture", f"{stats['avg_moisture']}%")


# =====================================================================
# PAGE 2: ANALYTICS & HISTORICAL TRENDS
# =====================================================================
elif page == "📈 Analytics & Historical Trends":
    st.title("📈 Telemetry Analytics & Trend Analysis")
    st.markdown("Detailed visual telemetry curves with threshold markers and environmental correlations.")

    cycles = get_cycles(uid, 500)
    if not cycles:
        st.info("No historical cycles recorded yet. Please run cycles on the Live Dashboard first.")
    else:
        df = pd.DataFrame(cycles).sort_values("id").reset_index(drop=True)
        df["cycle_num"] = range(1, len(df) + 1)

        # 1. Soil Moisture Control Chart with Thresholds
        st.subheader("1. Soil Moisture Hysteresis Tracking")
        fig_moisture = go.Figure()
        fig_moisture.add_trace(
            go.Scatter(
                x=df["cycle_num"],
                y=df["soil_moisture"],
                mode="lines+markers",
                name="Soil Moisture (%)",
                line=dict(color="#52b788", width=2.5),
            )
        )
        # Pump ON activation threshold line
        fig_moisture.add_hline(
            y=start_th,
            line_dash="dash",
            line_color="#e63946",
            annotation_text=f"Start Pump Threshold ({start_th:.0f}%)",
            annotation_position="bottom right",
        )
        # Pump OFF target threshold line
        fig_moisture.add_hline(
            y=stop_th,
            line_dash="dash",
            line_color="#457b9d",
            annotation_text=f"Stop Pump Threshold ({stop_th:.0f}%)",
            annotation_position="top right",
        )
        fig_moisture.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0c1d18",
            plot_bgcolor="#112922",
            height=380,
            xaxis_title="Simulation Cycle Number",
            yaxis_title="Moisture (%)",
        )
        st.plotly_chart(fig_moisture, use_container_width=True)

        # 2. Temperature, Humidity, and Tank Depletion
        st.subheader("2. Environmental & Reservoir Dynamics")
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            fig_temp_hum = px.line(
                df,
                x="cycle_num",
                y=["temperature", "humidity"],
                markers=True,
                title="Temperature (°C) & Relative Humidity (%)",
                color_discrete_map={"temperature": "#e76f51", "humidity": "#2a9d8f"},
            )
            fig_temp_hum.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0c1d18",
                plot_bgcolor="#112922",
                height=320,
                xaxis_title="Cycle Number",
            )
            st.plotly_chart(fig_temp_hum, use_container_width=True)

        with col_c2:
            fig_tank = px.area(
                df,
                x="cycle_num",
                y="tank_level",
                title="Reservoir Tank Water Level (%)",
                color_discrete_sequence=["#1d3557"],
            )
            fig_tank.add_hline(
                y=min_tank,
                line_dash="dot",
                line_color="#e63946",
                annotation_text=f"Safety Lock ({min_tank:.0f}%)",
            )
            fig_tank.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0c1d18",
                plot_bgcolor="#112922",
                height=320,
                xaxis_title="Cycle Number",
                yaxis_title="Tank Level (%)",
            )
            st.plotly_chart(fig_tank, use_container_width=True)

        # 3. Pump Actuation Timeline
        st.subheader("3. Pump Relay Actuation Log")
        df["pump_status_num"] = df["pump_state"].astype(int)
        fig_pump = px.bar(
            df,
            x="cycle_num",
            y="pump_status_num",
            title="Actuator State per Cycle (1 = Energized / ON, 0 = De-energized / OFF)",
            color="pump_status_num",
            color_continuous_scale=[[0, "#264653"], [1, "#2a9d8f"]],
        )
        fig_pump.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0c1d18",
            plot_bgcolor="#112922",
            height=260,
            yaxis=dict(tickvals=[0, 1], ticktext=["OFF", "ON"]),
            xaxis_title="Cycle Number",
        )
        st.plotly_chart(fig_pump, use_container_width=True)


# =====================================================================
# PAGE 3: ESP32 EMBEDDED ARCHITECTURE & PINOUT
# =====================================================================
elif page == "🔌 ESP32 Embedded Architecture":
    st.title("🔌 ESP32 Embedded Hardware & Systems Architecture")
    st.markdown("Detailed mapping of conceptual hardware controllers, sensor interfaces, and ADC math.")

    tab_pinout, tab_diagram, tab_adc = st.tabs(["📌 GPIO Pinout Table", "🗺️ Hardware Architecture", "🔢 12-Bit ADC Mathematics"])

    with tab_pinout:
        st.subheader("Target Microcontroller: ESP32-WROOM-32")
        pinout_data = [
            {
                "Pin / GPIO": "GPIO 34 (ADC1_CH6)",
                "Physical Component": "Capacitive Soil Moisture Sensor v1.2",
                "Interface Type": "Analog Input (0 - 3.3V)",
                "Electrical Characteristics": "High impedance, corrosion-resistant capacitive sensing plate.",
            },
            {
                "Pin / GPIO": "GPIO 4",
                "Physical Component": "DHT22 / DHT11 Sensor",
                "Interface Type": "Digital 1-Wire Serial",
                "Electrical Characteristics": "Calibrated digital signal with single-bus communication.",
            },
            {
                "Pin / GPIO": "GPIO 32 (ADC1_CH4 / Echo)",
                "Physical Component": "Ultrasonic Tank Level Sensor (JSN-SR04T)",
                "Interface Type": "Analog / Pulse Width",
                "Electrical Characteristics": "Waterproof ultrasonic transducer; measures time-of-flight to water surface.",
            },
            {
                "Pin / GPIO": "GPIO 26",
                "Physical Component": "5V 1-Channel Relay Module (Submersible Pump)",
                "Interface Type": "Digital Output (Active-LOW Optocoupler)",
                "Electrical Characteristics": "Optoisolated flyback protection. Driving a 12V DC diaphragm / submersible pump.",
            },
            {
                "Pin / GPIO": "VIN / 5V & 3.3V",
                "Physical Component": "Buck Converter / LM2596 Step-Down Module",
                "Interface Type": "Power Distribution Rails",
                "Electrical Characteristics": "Steps down 12V battery/solar supply to regulated 5V and 3.3V logic rails.",
            },
        ]
        st.table(pd.DataFrame(pinout_data))

    with tab_diagram:
        st.subheader("Data & Control Signal Flow")
        st.markdown(
            """
            ```
            [ Capacitive Soil Sensor ]  -->  GPIO 34 (12-bit ADC SAR)  \
            [ DHT22 Temp & Humidity  ]  -->  GPIO 04 (Single-Wire Bus) --> [ ESP32 SoC Firmware ]
            [ JSN-SR04T Tank Sensor  ]  -->  GPIO 32 (Echo Time/ADC)   /    (Hysteresis & Interlock)
                                                                                  |
                                                                                  v
            [ 12V Water Pump / Valve ]  <--  [ 5V Relay Optoisolator ] <--  GPIO 26 (Active LOW Out)
            ```
            """
        )
        st.info(
            "**Relay Active-Low Logic Note:** In industrial and embedded applications, relays are usually triggered with Active-LOW logic. "
            "Writing a logic `0` (GND) to the transistor base energizes the coil, while logic `1` (3.3V) keeps it open. "
            "This ensures failsafe behavior during bootloader initialization."
        )

    with tab_adc:
        st.subheader("ESP32 Successive Approximation Register (SAR) ADC Conversion")
        st.markdown(
            r"""
            The ESP32 features two 12-bit SAR ADCs. A 12-bit resolution divides the $3.3\,\text{V}$ reference into $2^{12} = 4096$ quantization levels ($0$ to $4095$):
            $$\text{ADC Count} = \left\lfloor \frac{V_{\text{in}}}{V_{\text{ref}}} \times 4095 \right\rfloor$$
            $$\text{Calculated Moisture \%} = \left( \frac{\text{ADC Count}}{4095} \right) \times 100\%$$
            """
        )
        st.markdown("##### Interactive ADC Converter")
        test_pct = st.slider("Test Moisture Percentage (%)", 0.0, 100.0, 42.0, step=0.5)
        res = calculate_adc_mapping(test_pct)
        c_a, c_b, c_c = st.columns(3)
        c_a.metric("Raw 12-bit Count", f"{res['adc_count']} / 4095")
        c_b.metric("Simulated Pin Voltage", f"{res['voltage']:.3f} V")
        c_c.metric("Hexadecimal Register", f"0x{res['adc_count']:03X}")


# =====================================================================
# PAGE 4: FAULT INJECTION TESTBENCH
# =====================================================================
elif page == "🧪 Fault Injection Testbench":
    st.title("🧪 Hardware Fault Injection & Failsafe Testbench")
    st.markdown("Demonstrate robust embedded failsafes during viva voce and technical evaluation.")

    st.write(
        "Industrial embedded systems must handle sensor disconnection, electrical shorts, and physical failures gracefully. "
        "Select a simulated fault condition below and verify the controller's safety response:"
    )

    fault_choice = st.radio(
        "Choose Injected Fault Scenario",
        [
            "Normal Operation",
            "Empty Water Tank",
            "Sensor Disconnected",
            "Sensor Short Circuit",
            "Thermal Warning",
        ],
        index=1,
    )

    if st.button("⚡ Inject Fault and Execute Failsafe Cycle", type="primary"):
        fault_telemetry = generate_sensor_reading(fault_injection=fault_choice)
        st.subheader("1. Injected Sensor Payload")
        st.json(fault_telemetry)

        decision = irrigation_decision(
            fault_telemetry,
            pump_on=True,  # Simulate pump actively running when fault occurs
            start_threshold=start_th,
            stop_threshold=stop_th,
            min_tank=min_tank,
        )

        st.subheader("2. Embedded Controller Response")
        if decision["pump_on"]:
            st.warning(f"Pump State: ON | Message: {decision['message']}")
        else:
            st.error(f"🛑 **FAILS-SAFE TRIGGERED:** Pump State: **OFF** | Relay: **{decision['relay_signal']}**")
            st.info(f"Reason: {decision['message']}")

        # Save cycle for reporting
        save_cycle(
            user_id=uid,
            reading={
                "soil_moisture": fault_telemetry.get("soil_moisture", 0.0) or 0.0,
                "temperature": fault_telemetry.get("temperature", 0.0) or 0.0,
                "humidity": fault_telemetry.get("humidity", 0.0) or 0.0,
                "tank_level": fault_telemetry.get("tank_level", 0.0) or 0.0,
                "adc_soil_count": 0,
                "adc_soil_voltage": 0.0,
            },
            pump_on=decision["pump_on"],
            message=decision["message"],
            input_mode="Fault Injection Test",
            crop_type=selected_crop,
            water_used_liters=0.0,
        )


# =====================================================================
# PAGE 5: PDF REPORTS & DATA EXPORT
# =====================================================================
elif page == "📑 PDF Reports & Data Export":
    st.title("📑 Historical Data Audit & PDF Export")
    st.markdown("Export simulation data for project documentation, college submission, or laboratory reports.")

    cycles = get_cycles(uid, 1000)
    stats = get_statistics(uid)

    if not cycles:
        st.warning("No records found in database. Run simulation cycles from the Live Dashboard to generate data.")
    else:
        df = pd.DataFrame(cycles).sort_values("id", ascending=False)

        col_d1, col_d2, col_d3 = st.columns([1.5, 1.5, 1.5])
        with col_d1:
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Download Telemetry CSV",
                csv_data,
                "agrisense_telemetry_history.csv",
                "text/csv",
                use_container_width=True,
            )

        with col_d2:
            pdf_bytes = make_pdf(current_user["username"], df, stats, crop_info)
            st.download_button(
                "📄 Download Official PDF Report",
                pdf_bytes,
                "agrisense_project_report.pdf",
                "application/pdf",
                type="primary",
                use_container_width=True,
            )

        with col_d3:
            if st.button("🗑️ Clear My Historical Records", use_container_width=True):
                clear_cycles(uid)
                st.success("Database records cleared.")
                time.sleep(0.5)
                st.rerun()

        st.subheader("Telemetry Data Table")
        display_cols = [
            "id",
            "created_at",
            "crop_type",
            "soil_moisture",
            "temperature",
            "humidity",
            "tank_level",
            "pump_state",
            "water_used_liters",
            "message",
        ]
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols], use_container_width=True, hide_index=True)


# =====================================================================
# PAGE 6: PROJECT REPORT & VIVA GUIDE
# =====================================================================
elif page == "🎓 Project Report & Viva Guide":
    st.title("🎓 Internship Project Summary & Viva Voce Guide")
    st.markdown("High-scoring answers, system specifications, and defense strategy.")

    st.subheader("Project Identification")
    st.markdown(
        """
        - **Official Title:** Software-Based Smart Agriculture Monitoring and Automated Irrigation Simulator
        - **Domain:** Embedded Systems, IoT, Computational Agro-Informatics
        - **Core Stack:** Python 3.10+, Streamlit, SQLite, Plotly Express, ReportLab
        - **Target Hardware Architecture:** Espressif ESP32 SoC + Capacitive ADC + Single-Bus DHT22 + Optocoupled Relay
        """
    )

    st.subheader("💡 Frequently Asked Viva Voce Questions & Answers")

    with st.expander("Q1: Why is this implemented as a software simulator rather than physical hardware?"):
        st.write(
            "**Answer:** The project simulates the complete control loop, ADC quantization, and sensor telemetry in software "
            "to rigorously test edge-case safety interlocks (such as low reservoir levels, sensor short circuits, and severe thermal stress) "
            "without risking physical pump burnout, pipe bursting, or sensor corrosion. It demonstrates that the embedded control "
            "algorithms are verified before burning firmware to silicon."
        )

    with st.expander("Q2: What is hysteresis and why is it necessary in irrigation control?"):
        st.write(
            "**Answer:** Simple single-threshold control causes 'relay chattering'. If the pump turns ON at 30% and OFF at 30%, "
            "small sensor fluctuations around 30% cause the relay to toggle on and off rapidly every few milliseconds, destroying "
            "the relay contacts and burning the motor coil. "
            "Hysteresis introduces a **deadband** (e.g., ON at 30%, OFF at 60%). Once triggered, the pump remains ON until "
            "the higher threshold is reached, ensuring smooth, durable duty cycles."
        )

    with st.expander("Q3: How does the ESP32 ADC quantize analog sensor readings?"):
        st.write(
            "**Answer:** The ESP32 contains a 12-bit Successive Approximation Register (SAR) ADC. It samples voltages between 0V and 3.3V, "
            "mapping them into 4096 discrete steps (0 to 4095). Capacitive soil moisture sensors produce analog voltages that scale "
            "inversely or directly with dielectric permittivity, which our software models using direct proportional scaling."
        )

    with st.expander("Q4: Explain the low-tank safety interlock."):
        st.write(
            "**Answer:** Centrifugal and submersible water pumps rely on water flow for cooling and impeller lubrication. "
            "If the soil is bone dry but the water reservoir is empty, running the pump would cause cavitation and thermal destruction. "
            "The low-tank interlock is a hardware-priority override: if tank level < minimum threshold (e.g., 10%), "
            "the pump is strictly held OFF regardless of how dry the soil is."
        )

    with st.expander("Q5: What hashing algorithm is used for user security in SQLite?"):
        st.write(
            "**Answer:** Passwords are never stored in plaintext. They are salted with a 16-byte cryptographically secure random token "
            "generated via `secrets.token_hex(16)` and hashed using `PBKDF2-HMAC-SHA256` with 150,000 iterations. Verification uses "
            "`secrets.compare_digest` to prevent timing attacks."
        )
