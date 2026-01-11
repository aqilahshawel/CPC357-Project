import cv2
import numpy as np
import serial
import time
import RPi.GPIO as GPIO 
from threading import Thread, Lock
from collections import Counter 

# --- AI LIBRARY ---
try:
    from ai_edge_litert.interpreter import Interpreter
except ImportError:
    import tensorflow.lite as tflite
    Interpreter = tflite.Interpreter

# --- CONFIGURATION ---
MODEL_PATH = "model_unquant.tflite"
LABELS_PATH = "labels.txt"
CAMERA_INDEX = 0 
THRESHOLD = 0.90
CAMERA_WIDTH = 640   
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
VERIFICATION_SAMPLES = 5 # Number of votes

# --- ULTRASONIC CONFIG ---
TRIG_PIN = 23
ECHO_PIN = 24
DISTANCE_THRESHOLD = 20 

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

# --- SERIAL SETUP ---
try:
    ser = serial.Serial("/dev/serial0", 115200, timeout=1)
    print("Serial Communication with Maker Feather Enabled")
except:
    print("Serial Error: Check if Serial is enabled in raspi-config")
    ser = None

# --- LOAD AI MODEL ---
interpreter = Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
height, width = input_details[0]['shape'][1], input_details[0]['shape'][2]

with open(LABELS_PATH, 'r') as f:
    labels = [line.strip().split(' ', 1)[-1].lower() for line in f.readlines()]

# --- CAMERA SETUP ---
cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
# BUFFERSIZE=1 helps, but manual flushing is safer
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 

print(f"System Ready. Waiting for object within {DISTANCE_THRESHOLD}cm...")

# --- GLOBALS ---
last_classification_time = 0
CLASSIFICATION_COOLDOWN = 5.0 

# State Variables
current_display_label = "READY"
current_display_color = (255, 255, 255) 
sensor_status_text = "Checking..."
sensor_status_color = (200, 200, 200)

def trigger_bin_serial(label):
    if ser:
        print(f">>> SENDING TO ESP32: {label}")
        ser.write(f"{label}\n".encode('utf-8'))

# --- HELPER: GET DISTANCE ---
def get_distance():
    GPIO.output(TRIG_PIN, False)
    time.sleep(0.000002)
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)
    
    pulse_start = time.time()
    pulse_end = time.time()
    timeout = time.time() + 0.04 
    
    while GPIO.input(ECHO_PIN) == 0:
        pulse_start = time.time()
        if pulse_start > timeout: return 100 
        
    while GPIO.input(ECHO_PIN) == 1:
        pulse_end = time.time()
        if pulse_end > timeout: return 100 
        
    duration = pulse_end - pulse_start
    return duration * 17150

# --- HELPER: CLASSIFY SINGLE FRAME ---
def classify_frame(frame):
    img = cv2.resize(frame, (width, height))
    input_data = np.expand_dims(img, axis=0)
    input_data = (np.float32(input_data) - 127.5) / 127.5

    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details[0]['index'])
    
    index = np.argmax(output_data[0])
    confidence = output_data[0][index]
    name = labels[index]
    return name, confidence

# --- UPDATED FUNCTION: VERIFY ITEM (WITH BUFFER FLUSH) ---
def verify_item_and_get_winner():
    votes = []
    print("--- Starting Verification Loop ---")
    
    # *** FIX: FLUSH THE BUFFER ***
    # This throws away the old frames sitting in memory
    for _ in range(4):
        cap.grab() 
    
    # Now take FRESH samples
    for i in range(VERIFICATION_SAMPLES):
        ret, frame = cap.read()
        if not ret: continue
        
        name, confidence = classify_frame(frame)
        
        # Log every vote
        print(f"  Sample {i+1}: {name.upper()} ({confidence*100:.1f}%)")
        
        if name != "background" and confidence >= THRESHOLD:
            votes.append(name)
            
    if not votes:
        return None 
        
    # Count votes
    vote_counts = Counter(votes)
    winner, count = vote_counts.most_common(1)[0]
    
    # Require at least 2 or 3 matching votes to be sure
    if count >= 2:
        print(f"--- Winner: {winner.upper()} ({count}/{VERIFICATION_SAMPLES}) ---")
        return winner
    else:
        print(f"--- Winner: {winner.upper()} (REJECTED: Only {count} votes) ---")
        return None

# --- MAIN LOOP ---
while True:
    ret, frame = cap.read()
    if not ret: 
        continue

    # 1. ULTRASONIC CHECK
    try:
        dist = get_distance()
    except:
        dist = 100

    if dist < DISTANCE_THRESHOLD and dist > 2:
        object_detected = True 
        sensor_status_text = f"STATUS: DETECTED ({int(dist)}cm)"
        sensor_status_color = (0, 0, 255) # Red
    else:
        object_detected = False
        sensor_status_text = f"STATUS: CLEAR ({int(dist)}cm)"
        sensor_status_color = (0, 255, 0) # Green

    current_time = time.time()
    
    # 2. TRIGGER LOGIC (With Voting)
    if object_detected and (current_time - last_classification_time > CLASSIFICATION_COOLDOWN):
        
        current_display_label = "VERIFYING..."
        current_display_color = (0, 255, 255) # Yellow
        
        # Force UI update
        cv2.putText(frame, f"ITEM: {current_display_label}", (10, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, current_display_color, 2)
        cv2.imshow("Smart Bin AI", frame)
        cv2.waitKey(1) 
        
        # --- START VOTING PROCESS ---
        final_decision = verify_item_and_get_winner()
        
        if final_decision:
            current_display_label = final_decision.upper()
            current_display_color = (0, 255, 0) # Green
            
            trigger_bin_serial(final_decision)
            last_classification_time = time.time()
            
        else:
            current_display_label = "UNCERTAIN"
            current_display_color = (0, 0, 255)
            last_classification_time = time.time()

    # 3. VISUAL FEEDBACK
    cv2.rectangle(frame, (0, 0), (640, 80), (0, 0, 0), -1) 
    cv2.putText(frame, f"ITEM: {current_display_label}", (10, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, current_display_color, 2)
    
    cv2.putText(frame, sensor_status_text, (10, 450), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, sensor_status_color, 2)

    cv2.imshow("Smart Bin AI", frame)

    if cv2.waitKey(1) == ord('q'): break

cap.release()
cv2.destroyAllWindows()
GPIO.cleanup()
