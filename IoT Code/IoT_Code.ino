#include <ESP32Servo.h>
#include <TinyGPS++.h>
#include <HardwareSerial.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// --- NETWORK CONFIG ---
const char* ssid = "munir";           
const char* password = "munirmunir";

// --- GCP VM CONFIG ---
const char* mqtt_server = "136.110.20.249";
const int mqtt_port = 1883;
const char* mqtt_topic = "smartbin/bin01/data";

// --- OBJECTS ---
WiFiClient espClient;
PubSubClient client(espClient);
TinyGPSPlus gps;

// ---------------- Servos ----------------
Servo paperServo;
Servo glassServo;
Servo metalServo;

const int PAPER_PIN = 17;
const int GLASS_PIN = 18;
const int METAL_PIN = 8;

// ---------------- Sensors & LED ----------------
const int LED_PIN = 14;
const int TRIG_PIN = 4;
const int ECHO_PIN = 5;
const long DISTANCE_THRESHOLD_CM = 10;

// ---------------- UARTs ----------------
// UART1 for Raspberry Pi Communication (RX=16, TX=15)
#define RX1_PIN 16  
#define TX1_PIN 15  
HardwareSerial MySerial(1);

// UART2 for GPS Module (RX=21)
#define RX2_PIN 21  
#define TX2_PIN 47 
HardwareSerial GPSSerial(2);

// ---------------- Globals ----------------
String command = "";
bool paperBinFull = false;
long lastDistance = -1;
String lastDetectedItem = "None";
unsigned long lastMsgTime = 0;

// --- WIFI SETUP ---
void setup_wifi() {
  delay(10);
  Serial.println("\nConnecting to WiFi...");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP: ");
  Serial.println(WiFi.localIP());
}

// --- MQTT RECONNECT ---
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection to GCP VM...");
    String clientId = "SmartBin-";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5s");
      delay(5000);
    }
  }
}

// --- ULTRASONIC SENSOR ---
long readDistanceCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return -1;
  return duration * 0.034 / 2;
}

// --- SEND DATA TO GCP VM ---
void sendTelemetry() {
  if (!client.connected()) reconnect();
  
  StaticJsonDocument<256> doc;
  doc["device_id"] = "bin01";
  doc["waste_level_cm"] = lastDistance;
  doc["is_full"] = paperBinFull;
  doc["last_item"] = lastDetectedItem;

  if (gps.location.isValid()) {
    doc["gps_lat"] = gps.location.lat();
    doc["gps_lng"] = gps.location.lng();
  } else {
    doc["gps_lat"] = 0.0;
    doc["gps_lng"] = 0.0;
  }

  char buffer[256];
  serializeJson(doc, buffer);
  client.publish(mqtt_topic, buffer);
  Serial.println("[MQTT SEND] " + String(buffer));
}

// --- HELPER: SMART DELAY ---
// Keeps MQTT alive and reads GPS while waiting for Servo
void smartDelay(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    client.loop(); // Keep MQTT connection alive
    // Keep reading GPS data so buffer doesn't overflow
    while (GPSSerial.available() > 0) {
      gps.encode(GPSSerial.read());
    }
  }
}

// --- SERVO CONTROL (UPDATED) ---
void openServo(Servo &servo) {
  servo.write(95); // Open
  
  // Wait 5 seconds (handling GPS + MQTT only)
  smartDelay(4000); 
  
  servo.write(0);  // Close
  
  // *** CRITICAL FIX: FLUSH BUFFER ***
  // Clear any commands received from Pi while the lid was open.
  // This prevents "ghost" re-opening.
  while(MySerial.available() > 0) {
    char t = MySerial.read(); // Read and discard
  }
  command = ""; // Clear the command string variable too
}

// ---------------- SETUP ----------------
void setup() {
  Serial.begin(115200);
  
  // Initialize UARTs
  MySerial.begin(115200, SERIAL_8N1, RX1_PIN, TX1_PIN);
  GPSSerial.begin(9600, SERIAL_8N1, RX2_PIN, TX2_PIN); 

  // Servos
  paperServo.attach(PAPER_PIN);
  glassServo.attach(GLASS_PIN);
  metalServo.attach(METAL_PIN);
  paperServo.write(0);
  glassServo.write(0);
  metalServo.write(0);

  // Pins
  pinMode(LED_PIN, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Connection
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  
  Serial.println("=== ESP32 Smart Bin (GCP VM) System Ready ===");
}

// ---------------- LOOP ----------------
void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  // 1. Process GPS Data (Continuous)
  while (GPSSerial.available() > 0) {
    gps.encode(GPSSerial.read());
  }

  // 2. Ultrasonic Monitoring
  // We use millis() to avoid blocking checks
  static unsigned long lastDistCheck = 0;
  if (millis() - lastDistCheck > 200) { // Check every 200ms
    long distance = readDistanceCM();
    lastDistCheck = millis();

    if (distance > 0) {
      // Logic: Update if change is significant OR if time elapsed
      if (abs(distance - lastDistance) > 2 || millis() - lastMsgTime > 10000) {
        lastDistance = distance;
        paperBinFull = (distance < DISTANCE_THRESHOLD_CM);
        digitalWrite(LED_PIN, paperBinFull ? HIGH : LOW);
        sendTelemetry();
        lastMsgTime = millis();
      }
    }
  }

  // 3. Process Logic from Raspberry Pi (AI Camera)
  while (MySerial.available()) {
    char c = MySerial.read();
    if (c == '\n') {
      command.trim();
      command.toLowerCase();
      
      // Filter out empty commands/noise
      if (command.length() == 0) continue;

      lastDetectedItem = command;
      Serial.println("[Pi Command] Detected: " + command);

      if (command == "paper") {
        if (!paperBinFull) {
          openServo(paperServo);
        } else {
          Serial.println("Paper bin FULL. Servo locked.");
          sendTelemetry(); 
        }
      }
      else if (command == "glass") {
        openServo(glassServo);
      }
      else if (command == "aluminium") {
        openServo(metalServo);
      }
  
      // Send immediate update to Cloud after an item is dropped
      sendTelemetry();
      command = "";
    } else {
      command += c;
    }
  }
}
