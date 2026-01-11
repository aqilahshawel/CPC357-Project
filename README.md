# Smart Bin IoT Project

This repository contains the full codebase for a smart bin IoT system, including:

- **AI Model** (Raspberry Pi + camera object detection)
- **IoT Code** (Arduino/ESP microcontroller firmware)
- **Cloud Bridge** (`bridge.py`, runs on a VM via SSH)
- **Monitoring Dashboard** (`app.py`, Streamlit web app)


---

## Repository Structure

- **AI Model/**
  - `model.py` – Python code to run the AI model on the Raspberry Pi (camera capture, inference, communication to bridge/cloud or IoT device).
  - `model_unquant.tflite` – TensorFlow Lite model file used for inference.
  - `labels.txt` – Class labels for the TFLite model.

- **IoT Code/**
  - `IoT_Code.ino` – Arduino IDE sketch for the microcontroller (sensors, actuators, communication with cloud/bridge).

- `app.py` – Streamlit dashboard for monitoring the smart bin status, viewing logs/metrics, and possibly sending control commands.
- `bridge.py` – Python script meant to run on a remote VM as a **bridge** between the IoT hardware and the cloud/database.

---

## Prerequisites

### Software

- **Arduino IDE** (for `IoT_Code.ino`).
- **Python 3.8+** on your development machine and VM.
- **Streamlit** and other Python dependencies for `app.py` and `bridge.py`.
- SSH access to a remote VM (Linux recommended) for running `bridge.py`.
- Optional: TensorFlow Lite runtime on Raspberry Pi for `AI Model/model.py`.

---

## Python Environment Setup (Local)

From the project root (this folder):

```bash
# 1) Create and activate virtual environment (example for Windows PowerShell)
python -m venv venv
./venv/Scripts/Activate.ps1

# 2) Install required packages (example – adjust as needed)
pip install streamlit firebase-admin requests opencv-python numpy
```

If you maintain a `requirements.txt`, you can instead run:

```bash
pip install -r requirements.txt
```

---

## Running the Streamlit Dashboard (app.py)

From the project root:

```bash
# Activate your virtual environment first, then:
streamlit run app.py
```

## Running the Bridge (bridge.py) on the VM

1. **Copy the project files** (or at least `bridge.py` and any required configs/credentials) to your VM.
2. **Install Python dependencies** on the VM (same as local, typically with `pip`).
3. Run:

```bash
python bridge.py
```

The bridge is responsible for:

- Receiving data from the IoT device and/or Raspberry Pi.
- Pushing data to the cloud (e.g., Firebase Realtime Database / Firestore).
- Optionally forwarding commands from the cloud/dashboard back to the IoT device.

Check `bridge.py` for:

- Host, port, or MQTT/Firebase configuration.
- Any hardcoded IP addresses or URLs that must match your network and cloud setup.

---

## Deploying the AI Model on Raspberry Pi (AI Model)

Typical workflow (adjust to your actual code in `model.py`):

1. Copy the `AI Model` directory to the Raspberry Pi.
2. Install dependencies (e.g., TensorFlow Lite runtime, OpenCV, numpy, etc.).
3. Connect and enable the camera module on the Pi.
4. Run:

```bash
python model.py
```

The script should:

- Capture frames from the camera.
- Run inference using `model_unquant.tflite`.
- Interpret predictions using `labels.txt`.
- Send results to the bridge/cloud or directly to the IoT device (depending on your implementation).

---