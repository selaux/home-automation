#define DEBUG true

#include <SPI.h>
#include "RF24.h"
#include "AESLib.h"
#ifdef DEBUG
#include "printf.h"
#endif

// "Hhno91h7man80azy"
const uint8_t key[] = {25, 123, 90, 174, 198, 145, 40, 33, 98, 90, 90, 111, 78, 65, 184, 188};
uint16_t myCounter = 0;
uint16_t serverCounter = 0;

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
    char data[4] = {0x12, 0x11, 0x10, 0x09};
    char received[32] = "";
    if (!registered) {
        registerWithServer();
    }
    delay(250);
    sendPacket(5, data, 4);
    waitForPacket(6, received, 500);
}

void setupRadio() {
    radio.begin();
    radio.setRetries(10, 10);
    radio.setChannel(0x4c);
    radio.setDataRate(RF24_250KBPS);
    radio.setPALevel(RF24_PA_HIGH);
    radio.setCRCLength(RF24_CRC_16);
    radio.setAutoAck(true);
    radio.enableDynamicPayloads();
    radio.enableAckPayload();

    radio.openWritingPipe(serverAddress);
    radio.openReadingPipe(1, listenAddress);
    radio.startListening();
#ifdef DEBUG
    radio.printDetails();
#endif
}

bool registerWithServer() {
    char received[32] = "";
    char payload[8] = "";
    bool registerSuccess = false;
    memcpy(&payload[0], &listenAddress, 8);

#ifdef DEBUG
    Serial.print("Registering: ");
#endif
    if (sendPacket(MESSAGE_REGISTER, payload, 8)) {
        if (waitForPacket(MESSAGE_REGISTER_ACK, received, 500)) {
            clientId = (uint8_t) received[4];
            memcpy(&serverId, &received[5], 8);
#ifdef DEBUG
            Serial.print("Success; ClientId: ");
            Serial.print(clientId);
            Serial.print("; ServerId: ");
            Serial.print((long) serverId);
            Serial.print(";\n");
#endif
            registerSuccess = true;
        }
    }
#ifdef DEBUG
    if (!registerSuccess) {
        Serial.print("Failed Registering;\n");
    }
#endif
    registered = registerSuccess;
    return registered;
}

bool waitForPacket(uint8_t type, char *data, int timeout) {
    unsigned long started_waiting_at = millis();
    bool hasTimedOut = false;
    bool correctPacket = false;

#ifdef DEBUG
    Serial.print("Waiting: ");
#endif
    while (!hasTimedOut && !correctPacket) {
        bool packetAvailable = readPacket(data);
        if (packetAvailable) {
            correctPacket = (uint8_t) data[2] == type;
        }
        hasTimedOut = millis() - started_waiting_at > timeout;
    }
#ifdef DEBUG
    if (!correctPacket) {
        Serial.print("Failed;\n");
    } else {
        Serial.print("Success;\n");
    }
#endif
    return correctPacket;
}

bool readPacket(char *data) {
    bool available = radio.available();
    bool goodPacket = false;
    uint16_t receivedCounter = 0;
    if (available) {
        radio.read(&data[0], 32);
        decryptPayload(data);
        receivedCounter = (data[0] << 8) | (data[31] & 0xFF);
        uint8_t receivedMessageId = data[2];
#ifdef DEBUG
        printCharArray("Receiving", data, 32);
#endif
        if (receivedMessageId != 1) {
            for (int i = 1; i < 11; i++) {
                if (receivedCounter == serverCounter + i) {
                    goodPacket = true;
                    serverCounter = receivedCounter;
                }
#ifdef DEBUG
                if (!goodPacket) {
                    Serial.print("Bad Counter: ");
                    Serial.print(receivedCounter);
                    Serial.print(" - ");
                    Serial.print(serverCounter);
                }
#endif
            }
        } else {
            goodPacket = true;
            serverCounter = receivedCounter;
        }
    }
    return available && goodPacket;
}

bool sendPacket(uint8_t type, char *payload, uint8_t payloadSize) {
    char data[32] = "";
    char ackData[8] = "";
    uint8_t counter_low = myCounter & 0xFF;
    uint8_t counter_high = myCounter >> 8;
    uint64_t receivedServerId;
    char receivedChecksum;
    bool success;
    memcpy(&data[0], &counter_high, 1);
    memcpy(&data[1], &clientId, 1);
    memcpy(&data[2], &type, 1);
    memcpy(&data[3], &payloadSize, 1);
    memcpy(&data[4], &payload[0], (int) payloadSize);
    for (int i = 0; i < MAX_PAYLOAD_SIZE - payloadSize; i++) {
        data[4 + payloadSize + i] = (uint8_t) random(0, 255);
    }
    memcpy(&data[31], &counter_low, 1);

#ifdef DEBUG
    printCharArray("Sending", data, 32);
#endif

    encryptPayload(data);

    radio.stopListening();
    success = radio.write(&data, 32);

#ifdef DEBUG
    if (!success) {
        Serial.print("Failed;\n");
    } else {
        Serial.print("Success;\n");
    }
#endif
    if (success) {
        myCounter++;
    }

    if (radio.isAckPayloadAvailable()) {
        radio.read(&ackData[0], 8);
        memcpy(&receivedServerId, &ackData[0], 8);
        memcpy(&receivedChecksum, &ackData[7], 1);
        if (type != MESSAGE_REGISTER && receivedServerId != serverId) {
            bool isCorruptedAckPayload = false;
            char calculatedChecksum = 0;
            for (int i = 0; i < 8; i++) {
                calculatedChecksum = calculatedChecksum & 0xFF ^ (ackData[i] << i) & 0xFF;
            }
            if (receivedChecksum != calculatedChecksum) {
                isCorruptedAckPayload = true;
            }

            if (!isCorruptedAckPayload) {
#ifdef DEBUG
                Serial.print("ACK Data: ");
                Serial.print((long) receivedServerId);
                Serial.print(" - ");
                Serial.print((long) serverId);
                Serial.print("; ");
                Serial.print(receivedChecksum);
                Serial.print(" - ");
                Serial.print(calculatedChecksum);
                Serial.print("; Unregistering;\n");
#endif
                registered = false;
            } else {
#ifdef DEBUG
                Serial.print("Ignoring corrupted ACK-data.");
                Serial.print("ACK Data: ");
                Serial.print((long) receivedServerId);
                Serial.print(" - ");
                Serial.print((long) serverId);
                Serial.print("; ");
                Serial.print(receivedChecksum);
                Serial.print(" - ");
                Serial.println(calculatedChecksum);
#endif
            }
        }
    }

    radio.startListening();

    return success;
}

#ifdef DEBUG
void printCharArray(char *label, char *data, int length) {
    Serial.print(label);
    Serial.print(": ");
    for (int i = 0; i < length; i++) {
        Serial.print((uint8_t) data[i], HEX);
        Serial.print(" ");
    }
}
#endif

void encryptPayload(char *data) {
    aes128_enc_single(key, data + 16);
    for (int i = 0; i < 16; i++) {
        data[i] = data[16 + i] ^ data[i];
    }
    aes128_enc_single(key, data);
}

void decryptPayload(char *data) {
    aes128_dec_single(key, data);
    for (int i = 0; i < 16; i++) {
        data[i] = data[16 + i] ^ data[i];
    }
    aes128_dec_single(key, data + 16);
}
