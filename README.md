# AstraNex-KshetraSaarthi
AI-powered smart farming assistant for Indian farmers using AI, IoT sensors, crop monitoring and intelligent decision support.
# 🌾 AstraNex — KshetraSaarthi

### AI-Powered Smart Farming Assistant for Indian Farmers

> **Empowering farmers with AI, IoT, real-time field intelligence and smarter agricultural decisions.**

---

## 🚀 About the Project

**KshetraSaarthi**, powered by **AstraNex**, is an AI-powered smart farming assistant designed with Indian farmers in mind.

The system combines **AI-based crop analysis, IoT/field sensors, weather information and intelligent decision support** to help farmers monitor their fields, identify potential crop problems early and make better decisions regarding irrigation, crop health and agricultural risks.

Instead of expecting farmers to interpret complex technical data, KshetraSaarthi converts field information into **simple, actionable recommendations**.

### Our Vision

To build a technology-driven agricultural ecosystem where farmers can receive timely, understandable and actionable information about their fields — helping improve productivity while reducing unnecessary input usage and water consumption.

---

# 🎯 Problem Statement

Farmers often face several challenges:

* 🌱 Crop diseases and pests may be detected too late.
* 💧 Irrigation decisions are often based on estimation rather than field conditions.
* 🌡️ Temperature and environmental changes can affect crop health.
* 🌦️ Extreme weather events can create significant agricultural risks.
* 🧪 Nutrient deficiencies can reduce crop productivity.
* 📊 Agricultural sensor data can be difficult for farmers to interpret.
* 📱 Existing digital agricultural tools may not always provide a simple farmer-first experience.

There is a need for a system that can transform **raw field data into simple and useful decisions for farmers**.

---

# 💡 Our Solution

KshetraSaarthi acts as a **digital farming companion**.

The system collects information from multiple sources and processes it through an intelligent decision layer.

### Data Sources

```text
Field Sensors
     │
     ├── Soil Moisture
     ├── Temperature
     ├── Water Level
     └── Other Environmental Data
            │
            ▼
     Weather Information
            │
            ▼
       AI Analysis
            │
            ▼
   Decision Support System
            │
            ▼
      KshetraSaarthi
            │
            ▼
     Farmer-Friendly
     Recommendations
```

The goal is to convert complex agricultural information into simple actions such as:

* 💧 Water the field
* 💧 Water only a small quantity
* ✅ No irrigation required
* 🌱 Monitor crop health
* 🦠 Investigate possible disease
* 🐛 Check for pest activity
* 🌦️ Prepare for weather-related risks

---

# ✨ Key Features

## 👨‍🌾 1. Farmer-First Interface

The platform is designed around the farmer rather than around technical data.

Important field information is presented using:

* Easy-to-understand cards
* Visual indicators
* Status gauges
* Alerts
* Simple recommendations
* Mobile-application-style navigation

---

## 💧 2. Smart Irrigation Monitoring

The system monitors field water conditions and provides an easy-to-understand status.

Example:

```text
🔴 LOW
→ Irrigation required

🟡 MODERATE
→ Irrigate with a smaller quantity

🟢 HEALTHY
→ No immediate irrigation required
```

This helps farmers avoid unnecessary water usage.

---

## 🌱 3. Crop Health Monitoring

KshetraSaarthi can assist in monitoring crop health using field information and AI-based analysis.

The objective is to identify potential crop problems early so that farmers can respond before the problem becomes severe.

---

## 🦠 4. AI-Based Plant/Disease Analysis

The prototype provides an image-analysis workflow for plant and crop health assessment.

A farmer can provide an image of a plant or affected crop area.

The analysis pipeline can be used to identify potential:

* Crop diseases
* Pest-related problems
* Crop health issues
* Other visible abnormalities

The result is presented separately so that the farmer can clearly understand the analysis and recommended action.

---

## 🌦️ 5. Weather & Agricultural Risk Awareness

Weather conditions can significantly affect agricultural productivity.

KshetraSaarthi incorporates environmental and weather-related information to help farmers remain aware of risks such as:

* Extreme heat
* Heavy rainfall
* Flood conditions
* Drought conditions
* Sudden environmental changes

---

## 📡 6. IoT / Field Sensor Integration

The system is designed around real-time field information from sensors.

Potential sensor inputs include:

* Soil moisture
* Temperature
* Water level
* Environmental conditions

The sensor data can then be processed by the decision-support layer.

---

## 🤖 7. Intelligent Decision Support

The core objective is not simply to display sensor readings.

Instead:

```text
Raw Data
   ↓
Data Processing
   ↓
AI / Rule-Based Analysis
   ↓
Risk & Condition Assessment
   ↓
Actionable Recommendation
   ↓
Farmer
```

This allows the system to move from **“data monitoring”** to **“decision support.”**

---

# 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │       FARM          │
                    │                     │
                    │  Crops / Soil /     │
                    │  Field Conditions   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    IoT Sensors      │
                    │                     │
                    │ Soil Moisture       │
                    │ Temperature         │
                    │ Water Level         │
                    │ Environment         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Backend Layer    │
                    │                     │
                    │ Data Processing     │
                    │ APIs                │
                    │ AI Inference        │
                    │ Decision Logic      │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
            ┌───────────────┐     ┌───────────────┐
            │ AI Crop       │     │ Weather &     │
            │ Analysis      │     │ Risk Analysis │
            └───────┬───────┘     └───────┬───────┘
                    │                     │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │ KshetraSaarthi      │
                    │ Decision Support     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Farmer Application  │
                    │                     │
                    │ Alerts              │
                    │ Recommendations     │
                    │ Field Status        │
                    │ Crop Health         │
                    └─────────────────────┘
```

---

# 🔄 Data Flow

### Step 1 — Field Data Collection

Sensors collect information from the agricultural field.

### Step 2 — Data Processing

The backend receives and processes the available field information.

### Step 3 — AI / Decision Analysis

The system analyses crop images, sensor readings and environmental information.

### Step 4 — Condition Assessment

The system determines the current field/crop condition.

### Step 5 — Recommendation

Relevant information is converted into a simple recommendation.

### Step 6 — Farmer Interaction

The farmer receives the result through the KshetraSaarthi interface.

---

# 🖥️ Technology Stack

### Frontend

* HTML
* CSS
* JavaScript
* Responsive UI
* Interactive dashboards
* Mobile-application-style interface

### Backend

* Python
* REST APIs
* Data processing
* AI inference pipeline
* Decision-support logic

### AI / Machine Learning

* Image-based crop analysis
* Plant disease analysis
* Crop-health assessment
* Intelligent recommendations

### IoT

* Soil moisture sensing
* Temperature sensing
* Water-level monitoring
* Environmental monitoring

### Data & External Services

* Weather information
* Agricultural datasets
* Crop/disease information
* Sensor data

> The exact technologies and models used in the final implementation should be listed here according to the deployed prototype.

---

# 📱 Farmer-Centric Design

A major design principle of KshetraSaarthi is:

> **Technology should adapt to the farmer — not the farmer to the technology.**

Instead of overwhelming users with raw numbers and technical terminology, the interface focuses on:

### What is happening?

🌱 Crop condition

### What needs attention?

⚠️ Potential problem

### What should I do?

💧 Irrigate / Monitor / Take action

### How urgent is it?

🔴 High
🟡 Medium
🟢 Healthy

---

# 🌍 Designed for Indian Agriculture

KshetraSaarthi is designed with the realities of Indian agriculture in mind.

The system aims to support farmers dealing with:

* Water scarcity
* Changing weather patterns
* Crop diseases
* Pest attacks
* Heat waves
* Heavy rainfall
* Flood risks
* Drought conditions
* Increasing agricultural input costs

Our long-term vision is to make intelligent agricultural technology **accessible, understandable and useful at the field level**.

---

# 📊 Prototype

The current repository contains the prototype developed for the **Internal Hackathon 2026 at RGUKT-AP**.

The prototype demonstrates the concept, user interface, field monitoring workflow, AI-assisted analysis and decision-support approach of KshetraSaarthi.

---

# 🏆 Hackathon

### Internal Hackathon 2026 — RGUKT-AP

KshetraSaarthi was developed and presented as part of the **Internal Hackathon 2026 at Rajiv Gandhi University of Knowledge Technologies, Andhra Pradesh (RGUKT-AP)**.

The Internal Hackathon provided an opportunity to develop, demonstrate and improve our solution as part of our journey toward the **Smart India Hackathon (SIH)**.

---

# 👥 Team

### Team Name

**AstraNex**

### Project

**AstraNex — KshetraSaarthi**

### Team Members

* **Harsha** — Team lead(Web developer)
* **Zubair** — AI translation developer
* **Karthik** — Simulaion
* **Mounika** — research on pests and their resistances
* **Chandrika** — PPT
* **Preethi** — Video editor and developer

### Institution

**Rajiv Gandhi University of Knowledge Technologies,ONGOLE
Andhra Pradesh (RGUKT-AP)**

---

# 👨‍🏫 Acknowledgements

We sincerely thank the **Director, SPOC, AO, faculty members, coordinators and organizers of RGUKT-AP** for their guidance, encouragement and support in providing students with an opportunity to participate in the Internal Hackathon 2026.

We are grateful to **RGUKT-AP and RGUKT Ongole** for encouraging innovation, technical learning and student participation in national-level innovation initiatives.

---

# 🚀 Future Scope

KshetraSaarthi can be further expanded with:

* 📡 Large-scale IoT deployment
* 🛰️ Satellite and remote-sensing data
* 🌦️ Advanced weather prediction
* 🤖 More accurate AI crop-disease models
* 🗣️ Regional-language voice interaction
* 📱 Android/iOS deployment
* 🗺️ Field mapping and geospatial intelligence
* 📈 Historical crop analytics
* 🔔 Personalized farmer alerts
* ☁️ Cloud synchronization
* 👨‍🌾 Multi-farm management
* 📊 Agricultural decision analytics

---

# 🎯 Our Goal

KshetraSaarthi is not just about detecting a problem.

It is about helping a farmer **understand the problem, respond at the right time and make a better decision.**

> **Detect early. Understand clearly. Act intelligently.**

### 🌾 AstraNex — KshetraSaarthi

### **Technology for Smarter Farms. Intelligence for Stronger Farmers.**

---

## 📜 License

This project is developed as a student innovation prototype for hackathon and educational purposes.

**© 2026 AstraNex / KshetraSaarthi Team**
