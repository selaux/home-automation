#define HOMEAUTOMATION_DEBUG true

#include "HomeAutomation.h"

#define MAX_PAYLOAD_SIZE 27
#define MESSAGE_REGISTER 0
#define MESSAGE_REGISTER_ACK 1
#define MESSAGE_PUB_CHANNEL 2
#define MESSAGE_SUB_CHANNEL 3
#define MESSAGE_PUB 4

#ifdef HOMEAUTOMATION_DEBUG
void printCharArray(char *label, char *data, int length) {
    Serial.print(label);
    Serial.print(": ");
    for (int i = 0; i < length; i++) {
        Serial.print((uint8_t) data[i], HEX);
        Serial.print(" ");
    }
}
#endif

HomeAutomation::HomeAutomation(RF24 *radio, uint64_t serverAddress, uint64_t listenAddress, uint8_t *key) {
    this->radio = radio;
    this->serverAddress = serverAddress;
    this->listenAddress = listenAddress;
    this->key = key;
    this->subscriptionHandlers = NULL;
    this->numberOfPublishChannels = 0;
    this->registered = false;
}

void HomeAutomation::begin() {
#ifdef HOMEAUTOMATION_DEBUG
        printf_begin();
#endif
    this->radio->begin();
    this->radio->setRetries(10, 10);
    this->radio->setChannel(0x4c);
    this->radio->setDataRate(RF24_250KBPS);
    this->radio->setPALevel(RF24_PA_HIGH);
    this->radio->setCRCLength(RF24_CRC_16);
    this->radio->setAutoAck(true);
    this->radio->enableDynamicPayloads();
    this->radio->enableAckPayload();

    this->radio->openWritingPipe(serverAddress);
    this->radio->openReadingPipe(1, listenAddress);
    this->radio->startListening();
#ifdef HOMEAUTOMATION_DEBUG
    this->radio->printDetails();
#endif
}

bool HomeAutomation::registerWithGateway() {
    char payload[8] = "";
    bool registerSuccess = false;
    memcpy(&payload[0], &listenAddress, 8);

    this->counter = random(0, 65535);

#ifdef HOMEAUTOMATION_DEBUG
        Serial.print("Registering;\n");
    #endif
    if (this->sendPacket(MESSAGE_REGISTER, payload, 8)) {
        char received[32] = "";
        if (this->waitForPacket(MESSAGE_REGISTER_ACK, received, 500)) {
            this->clientId = (uint8_t) received[4];
            memcpy(&(this->serverId), &received[5], 8);
#ifdef HOMEAUTOMATION_DEBUG
                Serial.print("Register Success; ClientId: ");
                Serial.print(clientId);
                Serial.print("; ServerId: ");
                Serial.print((long) serverId);
                Serial.print(";\n");
            #endif
            registerSuccess = true;
            if (this->subscriptionHandlers != NULL) {
                free(this->subscriptionHandlers);
                this->subscriptionHandlers = NULL;
            }
        }
    }
#ifdef HOMEAUTOMATION_DEBUG
        if (!registerSuccess) {
            Serial.print("Register Failed;\n");
        }
    #endif
    this->registered = registerSuccess;
    return registered;
}

bool HomeAutomation::isRegistered() {
    return this->registered;
}

void HomeAutomation::poll() {
    char received[32] = "";
    int  handlerSize = sizeof(void (*)(char*, uint8_t));
    int  currentHandlerListSize = sizeof(this->subscriptionHandlers) / handlerSize;

    if (this->readPacket(received)) {
        uint8_t messageType = received[2];
        if (messageType == MESSAGE_PUB) {
            uint8_t channel = received[4];
            uint8_t payloadSize = received[3];
            if (channel < currentHandlerListSize) {
                (*this->subscriptionHandlers[channel])(&received[5], payloadSize);
            }
        }
    }
}

uint8_t HomeAutomation::subscribeChannel(char* routingKey, uint8_t transformId, HandlerPointer handler) {
    int handlerSize = sizeof(HandlerPointer);
    uint8_t routingKeyLength = (uint8_t) strlen(routingKey);
    int channelId = this->subscriptionHandlers != NULL ? sizeof(this->subscriptionHandlers) / handlerSize : 0;
    char payload[32] = "";
    uint8_t payloadSize = routingKeyLength + 2;

    memcpy(&payload[0], &channelId, 1);
    memcpy(&payload[1], &transformId, 1);
    memcpy(&payload[2], &routingKey[0], routingKeyLength);

#ifdef HOMEAUTOMATION_DEBUG
    Serial.print("Register subscription of ");
    Serial.print(routingKey);
    Serial.print(" to channel ");
    Serial.println(channelId);
#endif

    if (this->sendPacket(MESSAGE_SUB_CHANNEL, payload, payloadSize)) {
        if (this->subscriptionHandlers == NULL) {
            this->subscriptionHandlers = (HandlerPointer*) malloc(handlerSize);
            this->subscriptionHandlers[channelId] = handler;
        } else {
            this->subscriptionHandlers = (HandlerPointer*) realloc(this->subscriptionHandlers, (channelId+1) * handlerSize);
            this->subscriptionHandlers[channelId] = handler;
        }
#ifdef HOMEAUTOMATION_DEBUG
        Serial.println("Subscribe success;");
#endif
    } else {
#ifdef HOMEAUTOMATION_DEBUG
        Serial.println("Subscribe failure;");
#endif
    }

    return channelId;
}

uint8_t HomeAutomation::publishChannel(char* routingKey, uint8_t transformId) {
    int channelId = this->numberOfPublishChannels;
    uint8_t routingKeyLength = (uint8_t) strlen(routingKey);
    char payload[32] = "";
    uint8_t payloadSize = routingKeyLength + 2;

    memcpy(&payload[0], &channelId, 1);
    memcpy(&payload[1], &transformId, 1);
    memcpy(&payload[2], &routingKey[0], routingKeyLength);

#ifdef HOMEAUTOMATION_DEBUG
    Serial.print("Register publishing of ");
    Serial.print(routingKey);
    Serial.print(" to channel ");
    Serial.println(channelId);
#endif

    if (this->sendPacket(MESSAGE_PUB_CHANNEL, payload, payloadSize)) {
        this->numberOfPublishChannels += 1;
#ifdef HOMEAUTOMATION_DEBUG
        Serial.println("Publishing success;");
#endif
    } else {
#ifdef HOMEAUTOMATION_DEBUG
        Serial.println("Publishing failure;");
#endif
    }

    return channelId;
}

bool HomeAutomation::publish(uint8_t channelId, char* data, uint8_t dataSize) {
    char payload[32] = "";
    uint8_t payloadSize = dataSize + 1;

    memcpy(&payload[0], &channelId, 1);
    memcpy(&payload[1], &data[0], dataSize);

    return this->sendPacket(MESSAGE_PUB, payload, payloadSize);
}

bool HomeAutomation::sendPacket(uint8_t type, char *payload, uint8_t payloadSize) {
    uint8_t retries = 10;
    char data[32] = "";
    bool ackDataAvailable;
    char ackData[8] = "";
    char receivedChecksum;
    bool success;

    uint8_t counter_low = this->counter & 0xFF;
    uint8_t counter_high = this->counter >> 8;
    uint64_t receivedServerId;

    memcpy(&data[0], &counter_high, 1);
    memcpy(&data[1], &clientId, 1);
    memcpy(&data[2], &type, 1);
    memcpy(&data[3], &payloadSize, 1);
    memcpy(&data[4], &payload[0], (int) payloadSize);
    for (int i = 0; i < MAX_PAYLOAD_SIZE - payloadSize; i++) {
        data[4 + payloadSize + i] = (uint8_t) random(0, 255);
    }
    memcpy(&data[31], &counter_low, 1);

#ifdef HOMEAUTOMATION_DEBUG
    printCharArray("Sending", data, 32);
#endif

    this->encryptPayload(data);

    this->radio->stopListening();
    while (!success && retries != 0) {
        success = this->radio->write(&data, 32);
        retries -= 1;
    }
    ackDataAvailable = this->radio->isAckPayloadAvailable();

    if (ackDataAvailable) {
        this->radio->read(&ackData[0], 8);
    }

    this->radio->startListening();

    if (success && ackDataAvailable) {
        memcpy(&receivedServerId, &ackData[0], 8);
        memcpy(&receivedChecksum, &ackData[7], 1);

        if (type != MESSAGE_REGISTER && receivedServerId != this->serverId) {
            char calculatedChecksum = this->calculateXORChecksum(ackData, 7);

            if (receivedChecksum != calculatedChecksum) {
                this->registered = false;
#ifdef HOMEAUTOMATION_DEBUG
                Serial.print(" ACK Data: ");
                Serial.print((long) receivedServerId);
                Serial.print(" - ");
                Serial.print((long) this->serverId);
                Serial.print("; ");
                Serial.print(receivedChecksum);
                Serial.print(" - ");
                Serial.print(calculatedChecksum);
                Serial.print("; Unregistering;");
#endif
            } else {
#ifdef DEBUG
                Serial.print("ACK Data: ");
                Serial.print((long) receivedServerId);
                Serial.print(" - ");
                Serial.print((long) this->serverId);
                Serial.print("; ");
                Serial.print(receivedChecksum);
                Serial.print(" - ");
                Serial.println(calculatedChecksum);
                Serial.print("Ignoring;");
#endif
            }
        }
    }

#ifdef HOMEAUTOMATION_DEBUG
    if (!success) {
        Serial.print("Failed;\n");
    } else {
        Serial.print("OK;\n");
    }
#endif

    if (success) {
        this->counter += 1;
    }

    return success;
}

bool HomeAutomation::readPacket(char *data) {
    bool available = this->radio->available();
    bool goodPacket = false;
    uint8_t client_id;
    uint16_t receivedCounter = 0;

    if (available) {
        this->radio->read(&data[0], 32);
        this->decryptPayload(data);

        receivedCounter = (data[0] << 8) | (data[31] & 0xFF);
        client_id = data[1];
        uint8_t receivedMessageId = data[2];

#ifdef HOMEAUTOMATION_DEBUG
        printCharArray("Receiving", data, 32);
#endif

        if (client_id == 0) {
            if (receivedMessageId != MESSAGE_REGISTER_ACK) {
                goodPacket = this->validateCounter(receivedCounter);
#ifdef HOMEAUTOMATION_DEBUG
                    if (!goodPacket) {
                        Serial.print("Bad Counter: ");
                        Serial.print(receivedCounter);
                        Serial.print(" - ");
                        Serial.print(this->serverCounter);
                        Serial.print("\n");
                    }
#endif
            } else {
                goodPacket = true;
            }
        } else {
            goodPacket = false;
#ifdef HOMEAUTOMATION_DEBUG
            Serial.print("Client Id from Server not 0;");
#endif
        }
    }

    if (goodPacket) {
        this->serverCounter = receivedCounter;
#ifdef HOMEAUTOMATION_DEBUG
        Serial.print("OK;\n");
#endif
    }

    return available && goodPacket;
}

bool HomeAutomation::validateCounter(uint16_t receivedCounter) {
    for (int i = 1; i <= 11; i++) {
        if (receivedCounter == this->serverCounter + i) {
            return true;
        }
    }
}

bool HomeAutomation::waitForPacket(uint8_t type, char *data, int timeout) {
    unsigned long started_waiting_at = millis();
    bool hasTimedOut = false;
    bool correctPacket = false;

#ifdef HOMEAUTOMATION_DEBUG
    Serial.print("Waiting:\n");
#endif
    while (!hasTimedOut && !correctPacket) {
        bool packetAvailable = this->readPacket(data);
        if (packetAvailable) {
            correctPacket = (uint8_t) data[2] == type;
        }
        hasTimedOut = millis() - started_waiting_at > timeout;
    }
#ifdef HOMEAUTOMATION_DEBUG
    if (!correctPacket) {
        Serial.print("Waiting Failed;\n");
    } else {
        Serial.print("Waiting Success;\n");
    }
#endif

    return !hasTimedOut && correctPacket;
}

char HomeAutomation::calculateXORChecksum(char *data, uint8_t dataLength) {
    char calculatedChecksum = 0;
    for (int i = 0; i <= dataLength; i++) {
        calculatedChecksum = calculatedChecksum & 0xFF ^ (data[i] << i) & 0xFF;
    }
    return calculatedChecksum;
}

void HomeAutomation::encryptPayload(char *data) {
    aes128_enc_single(this->key, data + 16);
    for (int i = 0; i < 16; i++) {
        data[i] = data[16 + i] ^ data[i];
    }
    aes128_enc_single(this->key, data);
}

void HomeAutomation::decryptPayload(char *data) {
    aes128_dec_single(this->key, data);
    for (int i = 0; i < 16; i++) {
        data[i] = data[16 + i] ^ data[i];
    }
    aes128_dec_single(this->key, data + 16);
}
