# 🌾 AstraNex — KshetraSaarthi

### AI-Powered Smart Farming Assistant for Indian Farmers

> **Turning field data into simple, actionable decisions for farmers.**

AstraNex — **KshetraSaarthi** is a farmer-centric smart agriculture prototype that combines **AI-assisted crop health analysis, IoT-based field monitoring, smart irrigation intelligence, environmental monitoring, and decision support** into a single platform.

The goal is simple: instead of forcing farmers to understand complex sensor values, technical dashboards, or isolated agricultural data, KshetraSaarthi converts field information into **clear, understandable and actionable recommendations**.

---

## 🚜 The Problem

Indian farmers face multiple challenges simultaneously:

* 🌱 Crop diseases and pest attacks
* 💧 Inefficient irrigation and water wastage
* 🌡️ Changing temperature and environmental conditions
* 🌦️ Weather-related agricultural risks
* 📡 Difficulty interpreting field sensor data
* 💰 Increased input costs
* ⏱️ Delayed identification of crop problems
* 📱 Lack of simple, farmer-friendly digital decision-support tools

Existing agricultural technologies often provide data, but **data alone does not always provide a decision**.

KshetraSaarthi focuses on closing this gap.

---

# 💡 Our Solution

KshetraSaarthi acts as a **digital farming assistant** that brings together field observations, sensor information and AI-assisted analysis.

The platform is designed to answer practical questions such as:

> **"Does my field need water?"**

> **"Is there a possible problem with my crop?"**

> **"What does this field condition mean?"**

> **"What should I do next?"**

Instead of displaying only technical measurements, the system translates them into **farmer-friendly status indicators and recommendations**.

---

# 👨‍🌾 Farmer-First Approach

KshetraSaarthi is designed around the farmer rather than around the technology.

### Farmer workflow

```text
Farmer Onboarding
        ↓
Crop & Location Setup
        ↓
Field Monitoring
        ↓
Sensor + Environmental Data
        ↓
AI / Decision Engine
        ↓
Crop & Field Assessment
        ↓
Simple Farmer Recommendation
        ↓
Action
```

The farmer-facing interface prioritizes:

* Simple language
* Visual indicators
* Clear alerts
* Action-oriented recommendations
* Easy navigation
* Mobile-application-style interaction

---

# 💧 Smart Irrigation Intelligence

One of the major farmer-facing features is simplified irrigation status.

Instead of asking a farmer to interpret raw soil-moisture values, KshetraSaarthi presents an understandable status.

### 🟢 HEALTHY

**No immediate irrigation required.**

### 🟡 MODERATE

**Apply a smaller quantity of water.**

### 🔴 LOW

**Irrigation is required.**

The objective is to support **efficient water usage** while reducing unnecessary irrigation.

---

# 🌱 Crop Health & Plant Analysis

KshetraSaarthi includes an image-analysis workflow for crop/plant health assessment.

### Analysis workflow

```text
Plant / Crop Image
        ↓
Image Processing
        ↓
AI-Assisted Inference
        ↓
Crop / Health Assessment
        ↓
Farmer-Friendly Result
        ↓
Recommended Action
```

The system is intended to assist with the early identification of potential crop-health problems and provide information in a form that is easier for farmers to understand.

> **Note:** AI-based predictions are intended as decision-support assistance and should not replace professional agricultural diagnosis when required.

---

# 📡 IoT & Field Monitoring

AstraNex also includes a hardware-oriented monitoring layer designed around field sensors.

The prototype demonstrates how agricultural sensor information can become part of the decision-making pipeline.

```text
Field Sensors
     ↓
Sensor Data
     ↓
Backend
     ↓
Data Processing
     ↓
Decision Engine
     ↓
Farmer Interface
```

The project also includes an **ESP32 sensor example** demonstrating the hardware integration concept.

---

# 🌡️ Environmental Monitoring

Field conditions can change rapidly.

KshetraSaarthi is designed to consider environmental information such as:

* 🌡️ Temperature
* 💧 Soil moisture
* 💦 Water availability
* 🌦️ Weather conditions
* 🌱 Crop/field health indicators

These signals can be combined to provide a more meaningful interpretation of field conditions.

---

# 🧠 Intelligent Decision Support

The core idea behind AstraNex is not simply:

> **"Collect data."**

It is:

> **"Understand the data and help the farmer decide what to do."**

The decision-support layer combines available field information and analysis results to produce understandable recommendations.

### Conceptual pipeline

```text
                 ┌─────────────────┐
                 │   Field Sensors │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Data Processing│
                 └────────┬────────┘
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
    Crop Image      Environmental      Sensor Data
     Analysis          Data
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                 ┌─────────────────┐
                 │ Decision Engine │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Farmer Guidance │
                 └─────────────────┘
```

---

# 🏗️ System Architecture

```text
┌──────────────────────────────────────────────┐
│              KshetraSaarthi UI              │
│      Farmer Dashboard / Monitoring / AI     │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                 Backend Layer                │
│       API / Processing / Decision Logic      │
└──────────────────────┬───────────────────────┘
                       │
        ┌──────────────┼───────────────┐
        ▼              ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ AI Analysis │ │ Sensor Data │ │ Field / Risk│
│   Pipeline  │ │   Pipeline  │ │ Information │
└─────────────┘ └─────────────┘ └─────────────┘
        │              │               │
        └──────────────┼───────────────┘
                       ▼
              ┌─────────────────┐
              │ Decision Engine │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │ Farmer Guidance │
              └─────────────────┘
```

---

# 📱 User Experience

The project is designed to move away from a traditional technical dashboard and toward a **farmer-friendly application experience**.

The interface focuses on:

### 🏠 Farmer Dashboard

A quick overview of important field conditions.

### 💧 Irrigation Status

Simple visual indication of whether irrigation is required.

### 🌱 Crop Health

Crop and plant-health information.

### 📡 Sensor Monitoring

Field sensor readings and system status.

### 🤖 AI Analysis

Plant/crop image analysis workflow.

### 🌦️ Environmental Information

Relevant environmental and weather-related information.

### ⚠️ Alerts & Recommendations

Important conditions presented in an actionable format.

---

# 🛠️ Technology

The repository contains the following major components:

### Frontend

* HTML
* CSS
* JavaScript
* Interactive farmer-facing interface

### Backend

* Python-based backend
* API and processing components
* Decision/analysis services

### AI

* Plant/crop image analysis pipeline
* Model preparation/inference workflow

### Database

* Local data-management components

### Hardware

* ESP32-based sensor integration example
* Agricultural field-monitoring concept

### Testing

* Automated backend tests and project test configuration

> The repository contains the implementation files for these components. Specific models, libraries and deployment configurations should be referenced directly from the corresponding source files.

---

# 📂 Project Structure

```text
AstraNex-KshetraSaarthi/
│
├── assets/
│   ├── india_map.png
│   └── plant_health_emojis.jpg
│
├── backend/
│   ├── main.py
│   ├── db.py
│   ├── engine.py
│   ├── schemas.py
│   ├── services/
│   │   ├── fusion.py
│   │   ├── inference.py
│   │   ├── irrigation.py
│   │   └── sensor_health.py
│   ├── models/
│   └── uploads/
│
├── hardware/
│   └── esp32_sensor_example.ino
│
├── scripts/
│   └── download_model.py
│
├── tests/
│   └── test_engine.py
│
├── astranex_frontend.html
├── AstraNex_Hardware_Prototype_Simulation_v4(1).htm
├── requirements.txt
├── run_backend.sh
├── prepare_ai_model.sh
├── START_HERE.md
├── VERSION.txt
├── pytest.ini
├── .gitignore
└── .env.example
```

---

# ⚙️ Running the Prototype

## 1. Clone the repository

```bash
git clone https://github.com/pothumahantyharshavardhan-creator/AstraNex-KshetraSaarthi.git
cd AstraNex-KshetraSaarthi
```

## 2. Create a Python virtual environment

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Start the backend

```bash
./run_backend.sh
```

If required, make the script executable:

```bash
chmod +x run_backend.sh
```

For additional project-specific setup, refer to:

```text
START_HERE.md
```

and:

```text
backend/README.md
```

---

# 🧪 Testing

The repository includes backend tests.

Run:

```bash
pytest
```

The test configuration is provided through:

```text
pytest.ini
```

---

# 🔬 Prototype Scope

AstraNex — KshetraSaarthi is currently a **prototype / proof-of-concept** demonstrating how AI, IoT and agricultural decision-support technologies can be brought together for farmer-centric applications.

The prototype establishes the software and hardware integration concepts required for a future field deployment.

---

# 🚀 Future Expansion

The platform can be extended toward real-world agricultural deployment through:

* 📡 Large-scale IoT sensor networks
* 🛰️ Satellite and remote-sensing data
* 🌦️ More advanced weather and climate intelligence
* 🤖 Improved crop/disease models
* 🗣️ Regional-language voice interaction
* 📱 Dedicated Android/mobile application
* 🔌 Offline-first field operation
* ☁️ Secure cloud synchronization
* 📊 Long-term crop and field history
* 🧪 Nutrient and soil-health analysis
* 🌾 Crop-specific recommendation models
* 👨‍🌾 Community and expert agricultural support

---

# 🎯 Our Vision

Our vision is to build a practical digital farming assistant that can help farmers make **faster, simpler and more informed decisions** using the information already available in their fields.

> **AstraNex doesn't aim to give farmers more data.
> It aims to turn data into decisions.**

---

# 🏆 Hackathon

AstraNex — KshetraSaarthi was developed as part of our **Internal Hackathon 2026 at RGUKT AP**, providing an opportunity to develop, demonstrate and improve our solution as part of our journey toward the **Smart India Hackathon (SIH)**.

The project focuses on applying technology to a real-world agricultural problem with an emphasis on **Indian farmers, practical field deployment and farmer-centric design**.

---

# 👥 Team

| Member        | Role                                  |
| ------------- | ------------------------------------- |
| **Harsha**    | Team Lead & Full-Stack/Web Developer  |
| **Zubair**    | AI & Translation Developer            |
| **Karthik**   | Hardware & Simulation                 |
| **Mounika**   | Agricultural Research & Pest Analysis |
| **Chandrika** | Presentation & Documentation          |
| **Preethi**   | Video Production & Development        |

---

# 🙏 Acknowledgements

We sincerely thank:

* **RGUKT AP**
* Our Director
* Our SPOC
* Our Administrative Officer
* Faculty mentors and coordinators
* Everyone who supported our Internal Hackathon journey

Their guidance and encouragement helped us develop and refine AstraNex — KshetraSaarthi.

---

# 📜 Disclaimer

AstraNex — KshetraSaarthi is a prototype developed for demonstration and hackathon purposes.

AI-generated crop-health assessments and recommendations are intended as **decision-support information** and should not be treated as a definitive agricultural diagnosis.

Real-world deployment would require extensive field validation, crop-specific datasets, sensor calibration, agronomic validation, security testing and farmer trials.

---

# 🌾 AstraNex — KshetraSaarthi

### **From Sensors to Intelligence. From Intelligence to Action.**

**Built with the vision of making smart agriculture more accessible to Indian farmers.**
