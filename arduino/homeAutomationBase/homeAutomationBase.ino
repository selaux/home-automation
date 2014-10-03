#include <SPI.h>
#include "nRF24L01.h"
#include "RF24.h"
#include "AESLib.h"
#include "printf.h"

// "Hhno91h7man80azy"
const uint8_t key[] = { 25, 123, 90, 174, 198, 145, 40, 33, 98, 90, 90, 111, 78, 65, 184, 188 };
uint8_t counter = 0;

RF24 radio(9, 10);
const uint64_t serverAddress = 0xF0F0F0F0E1LL;

uint64_t listenAddress = 0xF0F0F0F0D2LL;
uint8_t clientId = 0;

const uint8_t MESSAGE_REGISTER = 0;
const uint8_t MESSAGE_REGISTER_ACK = 1;


void setup() {
  Serial.begin(57600);
  printf_begin();
  setupRadio();
  registerWithServer();
}

void loop() {
}

void setupRadio() {
  radio.begin();
  radio.setRetries(15, 15);
  radio.setPALevel(RF24_PA_LOW);
  radio.setChannel(0x4c);
  radio.setDataRate(RF24_1MBPS);
  radio.setCRCLength(RF24_CRC_16);
  radio.setPayloadSize(32);
  radio.openWritingPipe(serverAddress);
  radio.openReadingPipe(1, listenAddress);
  radio.startListening();
  radio.printDetails();
}

void registerWithServer() {
  bool registered = false;
  char received[32] = "";
  
  char payload[8] = "";
  memcpy(&payload[0], &listenAddress, 8);
  
  while (!registered) {
    Serial.print("Registering: ");
    if (!sendPacket(MESSAGE_REGISTER, payload, 8)) {
        Serial.print("Failed sending packet;\n");
        delay(5000);
    } else {
        if (!waitForPacket(MESSAGE_REGISTER_ACK, received)) {
          Serial.print("Failed;\n");
          delay(5000);
        } else {
          clientId = (uint8_t)received[4];
          Serial.print("Success; ClientId: ");
          Serial.print(clientId);
          Serial.print(";\n");
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
  
  Serial.print("Waiting: ");
  while (!timeout && !correctPacket) {
    available = radio.available();
    if (available) {
      radio.read( &data[0], 32 );
      decryptPayload(data);
      Serial.print("Receiving: ");
        for (int i = 0; i < 32; i++) {
          Serial.print((uint8_t)data[i], HEX);
          Serial.print(" ");
        }
        Serial.print("\n");
      correctPacket = (uint8_t)data[2] == type;
    }
    timeout = millis() - started_waiting_at > 5000;
  }
  return correctPacket;
}

bool sendPacket(uint8_t type, char* payload, uint8_t payloadSize) {
  char data[32] = "";
  bool failed;
  memcpy(&data[0], &counter, 1);
  memcpy(&data[1], &clientId, 1);
  memcpy(&data[2], &type, 1);
  memcpy(&data[3], &payloadSize, 1);
  memcpy(&data[4], &payload[0], (int)payloadSize);
  counter++;

  Serial.print("Sending Before: ");
    Serial.print(counter);
    Serial.print(": ");
    for (int i = 0; i < 32; i++) {
      Serial.print((uint8_t)data[i], HEX);
      Serial.print(" ");
    }
    Serial.print("\n");

  encryptPayload(data);

  radio.stopListening();
  failed = radio.write( &data, 32 );
  radio.startListening();
  
  return failed;
}

void encryptPayload(char* data) {
  aes128_enc_single(key, data);
  for (int i = 0; i < 16; i++) {
      data[16+i] = data[16+i] ^ data[i];
  }
  aes128_enc_single(key, data + 16);
}

void decryptPayload(char* data) {
  aes128_dec_single(key, data + 16);
  for (int i = 0; i < 16; i++) {
      data[16+i] = data[16+i] ^ data[i];
  }
  aes128_dec_single(key, data);  
}
