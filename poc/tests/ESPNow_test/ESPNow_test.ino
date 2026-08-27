#include <WiFi.h>
#include <esp_now.h>

// ==========================================
// CONFIGURATION
// Set to 1 for the Master (connected to PC)
// Set to 0 for the Follower
// ==========================================
#define IS_MASTER 1

uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
uint32_t start_time = 0;
bool waiting_for_pong = false;

typedef struct struct_message {
  uint8_t type; // 1 for PING, 2 for PONG
} struct_message;

struct_message myData;

// Compatibility for ESP32 Core v3+
#if ESP_ARDUINO_VERSION_MAJOR >= 3
void OnDataRecv(const esp_now_recv_info_t *info, const uint8_t *incomingData, int len) {
#else
void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
#endif
  if (len != sizeof(struct_message)) {
    return;
  }

  struct_message msg;
  memcpy(&msg, incomingData, sizeof(msg));

  #if IS_MASTER
  // Master receives the PONG
  if (msg.type == 2 && waiting_for_pong) {
    uint32_t rtt = micros() - start_time;
    Serial.println(rtt); // Send RTT in microseconds to Python
    waiting_for_pong = false;
  }
  #else
  // Follower receives the PING and immediately echoes PONG
  if (msg.type == 1) {
    myData.type = 2;
    esp_now_send(broadcastAddress, (uint8_t *) &myData, sizeof(myData));
  }
  #endif
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  esp_now_register_recv_cb(OnDataRecv);

  // Register broadcast peer
  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;  
  peerInfo.encrypt = false;
  
  if (esp_now_add_peer(&peerInfo) != ESP_OK){
    Serial.println("Failed to add peer");
    return;
  }
}

void loop() {
  #if IS_MASTER
  // Check if Python sent the 'P' (Ping) command
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'P') {
      myData.type = 1;
      waiting_for_pong = true;
      start_time = micros();
      esp_now_send(broadcastAddress, (uint8_t *) &myData, sizeof(myData));
    }
  }
  #endif
}