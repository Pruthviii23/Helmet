// Helmate "helmet worn" link test. Flash the same sketch to both boards;
// each picks its role from its own MAC.
// Helmet: reads FSR (GPIO4) + Hall (GPIO3), sends state to the bike every 200 ms.
// Bike:   lights its blue LED (GPIO8, active LOW) while worn=1 and packets keep arriving.
#include <WiFi.h>
#include <esp_now.h>
#include <esp_idf_version.h>

const uint8_t HELMET_MAC[6] = {0x14, 0x63, 0x93, 0x6F, 0x0D, 0xBC};
const uint8_t BIKE_MAC[6]   = {0xE0, 0x72, 0xA1, 0x6D, 0x20, 0xA4};
const int FSR_PIN = 4, HALL_PIN = 3, LED_PIN = 8;
const int FSR_ON_MV = 350;          // above this = head inside
const uint32_t LINK_TIMEOUT_MS = 1000;  // bike: no packet for this long = treat as not worn

struct Packet { uint32_t seq; uint16_t fsr_mV; uint8_t hall; uint8_t worn; };

bool isHelmet = false;
volatile uint32_t acksOk = 0, acksFail = 0;
volatile Packet lastRx = {};
volatile uint32_t lastRxMs = 0, rxCount = 0;
uint32_t seq = 0;

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 5, 0)
void onSent(const wifi_tx_info_t *info, esp_now_send_status_t s) {
#else
void onSent(const uint8_t *mac, esp_now_send_status_t s) {
#endif
  if (s == ESP_NOW_SEND_SUCCESS) acksOk++; else acksFail++;
}

void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len != sizeof(Packet) || memcmp(info->src_addr, HELMET_MAC, 6) != 0) return;
  memcpy((void *)&lastRx, data, sizeof(Packet));
  lastRxMs = millis();
  rxCount++;
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);  // off
  pinMode(HALL_PIN, INPUT_PULLUP);
  analogReadResolution(12);
  delay(1500);
  WiFi.mode(WIFI_STA);
  WiFi.setTxPower(WIFI_POWER_8_5dBm);  // SuperMini antenna fix, keep in every sketch
  uint8_t me[6];
  WiFi.macAddress(me);
  isHelmet = memcmp(me, HELMET_MAC, 6) == 0;
  Serial.printf("\nBOOT %s role=%s\n", WiFi.macAddress().c_str(), isHelmet ? "HELMET" : "BIKE");
  if (esp_now_init() != ESP_OK) { Serial.println("ERROR esp_now_init"); return; }
  esp_now_register_send_cb(onSent);
  esp_now_register_recv_cb(onRecv);
  esp_now_peer_info_t p = {};
  memcpy(p.peer_addr, isHelmet ? BIKE_MAC : HELMET_MAC, 6);
  esp_now_add_peer(&p);
}

void loop() {
  if (isHelmet) {
    Packet pk;
    pk.seq = seq++;
    pk.fsr_mV = analogReadMilliVolts(FSR_PIN);
    pk.hall = digitalRead(HALL_PIN) == LOW;  // 1 = magnet near
    pk.worn = pk.hall && pk.fsr_mV > FSR_ON_MV;
    digitalWrite(LED_PIN, pk.worn ? LOW : HIGH);  // helmet LED mirrors its own decision
    esp_now_send(BIKE_MAC, (uint8_t *)&pk, sizeof(pk));
    Serial.printf("HELMET seq=%lu fsr_mV=%u hall=%u worn=%u ackOk=%lu ackFail=%lu\n",
                  (unsigned long)pk.seq, pk.fsr_mV, pk.hall, pk.worn,
                  (unsigned long)acksOk, (unsigned long)acksFail);
  } else {
    bool fresh = rxCount > 0 && millis() - lastRxMs < LINK_TIMEOUT_MS;
    bool worn = fresh && lastRx.worn;
    digitalWrite(LED_PIN, worn ? LOW : HIGH);
    Serial.printf("BIKE rx=%lu fresh=%d seq=%lu fsr_mV=%u hall=%u worn=%u LED=%s\n",
                  (unsigned long)rxCount, fresh, (unsigned long)lastRx.seq, lastRx.fsr_mV,
                  lastRx.hall, lastRx.worn, worn ? "ON" : "off");
  }
  delay(200);
}
