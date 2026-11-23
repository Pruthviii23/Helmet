// Helmet sensor test: FSR divider on GPIO4 (analog), A3144 Hall OUT on GPIO3 (digital, LOW = magnet).
#include <WiFi.h>
const int FSR_PIN = 4;
const int HALL_PIN = 3;

void setup() {
  Serial.begin(115200);
  pinMode(HALL_PIN, INPUT_PULLUP);
  analogReadResolution(12);
  WiFi.mode(WIFI_STA);
  delay(1500);
  Serial.printf("MAC %s\n", WiFi.macAddress().c_str());
}

void loop() {
  int raw = analogRead(FSR_PIN);
  int mv = analogReadMilliVolts(FSR_PIN);
  int hall = digitalRead(HALL_PIN);
  Serial.printf("t=%lu fsr_raw=%d fsr_mV=%d hall=%d%s\n", millis(), raw, mv, hall, hall == LOW ? " MAGNET" : "");
  delay(200);
}
