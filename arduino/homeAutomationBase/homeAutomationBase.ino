#include <SPI.h>
#include "RF24.h"
#include "AESLib.h"
#include "printf.h"

#define DEBUG true

// "Hhno91h7man80azy"
const uint8_t key[] = { 25, 123, 90, 174, 198, 145, 40, 33, 98, 90, 90, 111, 78, 65, 184, 188 };
uint16_t myCounter = 0;

RF24 radio(9, 10);
const uint64_t serverAddress = 0xF0F0F0F0E1LL;
uint64_t serverId;

uint64_t listenAddress = 0xF0F0F0F0D2LL;
uint8_t clientId = 0;

const uint8_t MAX_PAYLOAD_SIZE = 27;
const uint8_t MESSAGE_REGISTER = 0;
const uint8_t MESSAGE_REGISTER_ACK = 1;

bool registered = false;

void setup() {
  #ifdef DEBUG
  Serial.begin(57600);
  printf_begin();
  #endif
  setupRadio();
  delay(100);
  randomSeed(analogRead(0));
  myCounter = random(0, 65535);
}

void loop() {
  char data[4] = { 0x12, 0x11, 0x10, 0x09 };
  if (!registered) {
    registerWithServer();
  }
  delay(2500);
  sendPacket(5, data, 4);
}

void setupRadio() {
  radio.begin();
  radio.setRetries(15, 15);
  radio.setChannel(0x4c);
  radio.setDataRate(RF24_1MBPS);
  radio.setPALevel(RF24_PA_HIGH);
  radio.setCRCLength(RF24_CRC_16);
  radio.setAutoAck(true);
  radio.enableDynamicPayloads();
  radio.enableAckPayload();

  radio.openWritingPipe(serverAddress);
  radio.openReadingPipe(1, listenAddress);
  radio.startListening();
  radio.printDetails();
}

void registerWithServer() {
  char received[32] = "";
  char payload[8] = "";
  memcpy(&payload[0], &listenAddress, 8);
  
  while (!registered) {
    #ifdef DEBUG
    Serial.print("Registering: ");
    #endif
    if (!sendPacket(MESSAGE_REGISTER, payload, 8)) {
        #ifdef DEBUG
        Serial.print("Failed sending packet;\n");
        #endif
        delay(5000);
    } else {
        if (!waitForPacket(MESSAGE_REGISTER_ACK, received)) {
          #ifdef DEBUG
          Serial.print("Failed;\n");
          #endif
          delay(5000);
        } else {
          clientId = (uint8_t)received[4];
          memcpy(&serverId, &received[5], 8);
          #ifdef DEBUG
          Serial.print("Success; ClientId: ");
          Serial.print(clientId);
          Serial.print("; ServerId: ");
          Serial.print((long)serverId);
          Serial.print(";\n");
          #endif
          registered = true;
        }
    }
  }
}

bool waitForPacket(uint8_t type, char* data) {
  unsigned long started_waiting_at = millis();
  bool timeout = false;
  bool correctPacket = false;
  bool available = false;
  
  #ifdef DEBUG
  Serial.print("Waiting: ");
  #endif
  while (!timeout && !correctPacket) {
    available = radio.available();
    if (available) {
      radio.read( &data[0], 32 );
      decryptPayload(data);
      #ifdef DEBUG
      printCharArray("Receiving", data, 32);
      #endif
      correctPacket = (uint8_t)data[2] == type;
    }
    timeout = millis() - started_waiting_at > 5000;
  }
  return correctPacket;
}

bool sendPacket(uint8_t type, char* payload, uint8_t payloadSize) {
  char data[32] = "";
  char ackData[8] = "";
  uint8_t counter_low = myCounter & 0xFF;
  uint8_t counter_high = myCounter  >> 8;
  uint64_t receivedServerId;
  bool success;
  memcpy(&data[0], &counter_high, 1);
  memcpy(&data[1], &clientId, 1);
  memcpy(&data[2], &type, 1);
  memcpy(&data[3], &payloadSize, 1);
  memcpy(&data[4], &payload[0], (int)payloadSize);
  for (int i = 0; i < MAX_PAYLOAD_SIZE - payloadSize; i++) {
    data[4+payloadSize+i] = (uint8_t) random(0,255);
  }
  memcpy(&data[31], &counter_low, 1);

  #ifdef DEBUG
  printCharArray("Sending", data, 32);
  #endif

  encryptPayload(data);

  radio.stopListening();
  success = radio.write( &data, 32 );

  if (success) {
    myCounter++;
  }

  if (radio.isAckPayloadAvailable()) {
    radio.read( &receivedServerId, 8 );
    if (type != MESSAGE_REGISTER && receivedServerId != serverId) {
        #ifdef DEBUG
        Serial.print("ACK Data: ");
        Serial.print((long)receivedServerId);
        Serial.print(" - ");
        Serial.print((long)serverId);
        Serial.print("\n");
        #endif
        registered = false;
    }
  }

  radio.startListening();

  return success;
}

#ifdef DEBUG
void printCharArray(char* label, char* data, int length) {
    Serial.print(label);
    Serial.print(": ");
    for (int i = 0; i < length; i++) {
      Serial.print((uint8_t)data[i], HEX);
      Serial.print(" ");
    }
    Serial.print("\n");
}
#endif

void encryptPayload(char* data) {
  aes128_enc_single(key, data + 16);
  for (int i = 0; i < 16; i++) {
      data[i] = data[16+i] ^ data[i];
  }
  aes128_enc_single(key, data);
}

void decryptPayload(char* data) {
  aes128_dec_single(key, data);
  for (int i = 0; i < 16; i++) {
      data[i] = data[16+i] ^ data[i];
  }
  aes128_dec_single(key, data + 16);
}
