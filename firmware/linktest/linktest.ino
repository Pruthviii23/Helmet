// Helmate ESP-NOW link test. Flash the same sketch to both boards.
// 1. Each board broadcasts "HELLO" until it hears the other one.
// 2. It then adds the other board as a peer and sends direct "PING n"
//    messages. Direct sends are acknowledged by the receiver's radio,
//    so "ACK ok" in the log proves two-way delivery.
#include <WiFi.h>
#include <esp_now.h>
#include <esp_idf_version.h>

uint8_t broadcastMac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
uint8_t peerMac[6];
volatile bool havePeer = false;
volatile bool peerPending = false;
volatile uint32_t acksOk = 0, acksFail = 0, received = 0;
uint32_t sent = 0;

String macToStr(const uint8_t *m) {
  char b[18];
  snprintf(b, sizeof(b), "%02X:%02X:%02X:%02X:%02X:%02X", m[0], m[1], m[2], m[3], m[4], m[5]);
  return String(b);
}

void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  received++;
  char msg[64];
  int n = len < 63 ? len : 63;
  memcpy(msg, data, n);
  msg[n] = 0;
  Serial.printf("RX from %s rssi=%d: %s\n", macToStr(info->src_addr).c_str(),
                info->rx_ctrl ? info->rx_ctrl->rssi : 0, msg);
  if (!havePeer && !peerPending) {
    memcpy(peerMac, info->src_addr, 6);
    peerPending = true;  // add the peer from loop(), not from the callback
  }
}

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 5, 0)
void onSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
#else
void onSent(const uint8_t *mac, esp_now_send_status_t status) {
#endif
  if (!havePeer) return;  // broadcasts are never acknowledged
  if (status == ESP_NOW_SEND_SUCCESS) acksOk++; else acksFail++;
}

void addPeer(const uint8_t *mac) {
  esp_now_peer_info_t p = {};
  memcpy(p.peer_addr, mac, 6);
  p.channel = 0;
  p.encrypt = false;
  if (!esp_now_is_peer_exist(mac)) esp_now_add_peer(&p);
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  WiFi.mode(WIFI_STA);
  // Many C3 SuperMini boards transmit badly at full power (weak antenna layout).
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  delay(100);
  Serial.printf("\nBOOT my MAC: %s txpower=%d\n", WiFi.macAddress().c_str(), (int)WiFi.getTxPower());
  if (esp_now_init() != ESP_OK) {
    Serial.println("ERROR esp_now_init failed");
    return;
  }
  esp_now_register_recv_cb(onRecv);
  esp_now_register_send_cb(onSent);
  addPeer(broadcastMac);
}

void loop() {
  if (peerPending && !havePeer) {
    addPeer(peerMac);
    havePeer = true;
    peerPending = false;
    Serial.printf("PAIRED with %s\n", macToStr(peerMac).c_str());
  }

  char msg[48];
  if (havePeer) {
    snprintf(msg, sizeof(msg), "PING %lu", (unsigned long)sent);
    esp_now_send(peerMac, (uint8_t *)msg, strlen(msg));
  } else {
    snprintf(msg, sizeof(msg), "HELLO %lu", (unsigned long)sent);
    esp_now_send(broadcastMac, (uint8_t *)msg, strlen(msg));
  }
  sent++;

  if (sent % 5 == 0) {
    Serial.printf("STATS me=%s peer=%s sent=%lu received=%lu ackOk=%lu ackFail=%lu\n",
                  WiFi.macAddress().c_str(), havePeer ? macToStr(peerMac).c_str() : "none",
                  (unsigned long)sent, (unsigned long)received,
                  (unsigned long)acksOk, (unsigned long)acksFail);
  }
  delay(1000);
}
