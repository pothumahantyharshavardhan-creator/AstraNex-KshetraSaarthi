/* AstraNex KshetraSaarthi — ESP32 sensor proof-of-concept v1.0
   Reads soil moisture + DHT22 and posts JSON to the FastAPI backend.
   This sketch is a prototype: it does not autonomously control a pump/valve.
*/
#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

#define DHTPIN 4
#define DHTTYPE DHT22
#define SOIL_PIN 34
DHT dht(DHTPIN, DHTTYPE);

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASS = "YOUR_PASSWORD";
const char* API_URL = "http://192.168.1.10:8000/api/sensors";
const char* DEVICE_ID = "KS-001";
const char* FIRMWARE = "esp32-proof-v1.0";

unsigned long lastSend = 0;
const unsigned long SEND_EVERY_MS = 15000;

float readSoilPercent() {
  int raw = analogRead(SOIL_PIN);
  float pct = 100.0f - (raw / 4095.0f) * 100.0f;
  return constrain(pct, 0.0f, 100.0f);
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Wi-Fi");
  unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 10000) {
    delay(300); Serial.print(".");
  }
  Serial.println();
  Serial.println(WiFi.status() == WL_CONNECTED ? "Wi-Fi connected" : "Wi-Fi unavailable; will retry");
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  analogReadResolution(12);
  connectWiFi();
}

void loop() {
  if (millis() - lastSend < SEND_EVERY_MS) { delay(100); return; }
  lastSend = millis();

  if (WiFi.status() != WL_CONNECTED) connectWiFi();

  float soil = readSoilPercent();
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("DHT22 read failed; skipping sample");
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Offline sample retained conceptually; no server request made");
    return;
  }

  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  String body = "{";
  body += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  body += "\"field_id\":1,";
  body += "\"soil_moisture\":" + String(soil, 1) + ",";
  body += "\"temperature\":" + String(temperature, 1) + ",";
  body += "\"humidity\":" + String(humidity, 1) + ",";
  body += "\"timestamp\":" + String(millis() / 1000.0f, 1) + ",";
  body += "\"firmware_version\":\"" + String(FIRMWARE) + "\",";
  body += "\"battery\":100";
  body += "}";

  int code = http.POST(body);
  Serial.printf("Sensor POST -> HTTP %d | soil %.1f%% | %.1f C | %.1f%% RH\n", code, soil, temperature, humidity);
  http.end();
}
