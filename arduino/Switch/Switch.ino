#include <Arduino.h>
#include <SPI.h>
#include "RF24.h"
#include "AESLib.h"
#include "HomeAutomation.h"

uint8_t key[] = {25, 123, 90, 174, 198, 145, 40, 33, 98, 90, 90, 111, 78, 65, 184, 188};
RF24 radio(9,10);
HomeAutomation ha(
    &radio,
    0xF0F0F0F0E1LL,
    0xF0F0F0F0D2LL,
    key
);
uint8_t publishChannel;

unsigned long lastSend;
int switchTransformId = 0;
int outputPin = 5;
int status = HIGH;

void setup() {
    Serial.begin(57600);
    ha.begin();
    randomSeed(analogRead(0));
    delay(100);
    lastSend = millis();
    setSwitch();
}

void loop() {
    unsigned long now = millis();

    if (now - lastSend > 1000) {
        if (!ha.isRegistered()) {
            ha.registerWithGateway();
            registerChannels();
        }
        publishGet();
        lastSend = now;
    }
    delay(50);
    ha.poll();
}

void registerChannels() {
    ha.subscribeChannel("switch1.set", 11, switchTransformId, &handleSet);
    publishChannel = ha.publishChannel("switch1.get", 11, switchTransformId);
}

void publishGet() {
    char payload[1] = "";
    bool on = (status == HIGH);
    memcpy(&on, &payload[0], 1);
    ha.publish(publishChannel, payload, 1);
}

void handleSet(char* payload, uint8_t payloadSize) {
    Serial.println("Handle Set");
    bool on;
    memcpy(&payload[0], &on, 1);
    status = on ? HIGH : LOW;
    setSwitch();
}

void setSwitch() {
    digitalWrite(outputPin, status);
}
