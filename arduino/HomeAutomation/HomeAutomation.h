#ifndef HomeAutomation_h
#define HomeAutomation_h

#include <Arduino.h>
#include <SPI.h>
#include "RF24.h"
#include "AESLib.h"
#include "types.h"
#ifdef HOMEAUTOMATION_DEBUG
#include "printf.h"
#endif

class HomeAutomation
{
  public:
    HomeAutomation(RF24 *radio, uint64_t serverAddress, uint64_t listenAddress, uint8_t* key);
    void begin();
    bool registerWithGateway();
    bool isRegistered();
    void poll();
    uint8_t subscribeChannel(char* routingKey, uint8_t routingKeyLength, uint8_t transformId, HandlerPointer handler);
    uint8_t publishChannel(char* routingKey, uint8_t routingKeyLength, uint8_t transformId);
    bool publish(uint8_t channelId, char* payload, uint8_t payloadSize);

  private:
    RF24 *radio;

    uint64_t serverAddress;
    uint64_t listenAddress;
    uint8_t *key;

    bool registered;
    uint8_t clientId;
    uint64_t serverId;
    uint16_t counter;
    uint16_t serverCounter;

    HandlerPointer *subscriptionHandlers;
    uint8_t numberOfPublishChannels;

  protected:
    bool sendPacket(uint8_t type, char *payload, uint8_t payloadSize);
    bool readPacket(char *data);
    bool validateCounter(uint16_t receivedCounter);
    bool waitForPacket(uint8_t type, char *data, int timeout);
    char calculateXORChecksum(char *data, uint8_t dataLength);
    void encryptPayload(char *data);
    void decryptPayload(char *data);
};

#endif
