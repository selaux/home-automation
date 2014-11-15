#include <Arduino.h>
#include <SPI.h>
#include "LowPower.h"
#include <DHT.h>
#include "RF24.h"
#include "AESLib.h"
#include "HomeAutomation.h"

uint8_t key[] = {25, 123, 90, 174, 198, 145, 40, 33, 98, 90, 90, 111, 78, 65, 184, 188};
RF24 radio(9,10);
HomeAutomation ha(
    &radio,
    0xF0F0F0F0E1LL,
    0xF0F0F0F0A2LL,
    key
);

const unsigned long logAfterNumberOfSleepPeriods = 32;
unsigned long numberOfSleepPeriodsSinceLastLog = 31;
uint8_t temperatureTransformId = 1;
uint8_t publishChannel;

const uint8_t dht11Pin = 3;
const uint8_t dht11VccPin = 4;
DHT temperatureSensor;

void setup() {
    pinMode(dht11VccPin, OUTPUT);
    temperatureSensor.setup(dht11Pin);
    Serial.begin(57600);
    ha.begin();
    randomSeed(analogRead(0));
    delay(100);
}

void loop() {
    if (numberOfSleepPeriodsSinceLastLog == logAfterNumberOfSleepPeriods - 1) {
        digitalWrite(dht11VccPin, HIGH);
        powerDown();
    } else if (numberOfSleepPeriodsSinceLastLog == logAfterNumberOfSleepPeriods) {
        temperatureSensor.resetTimer();
        publishTemperature();
        digitalWrite(dht11VccPin, LOW);
        numberOfSleepPeriodsSinceLastLog = 0;
    } else {
        powerDown();
    }
}

void publishTemperature() {
    float temperature = temperatureSensor.getTemperature();;
    float humidity = temperatureSensor.getHumidity();

    char payload[8] = "";
    memcpy(&payload[0], &temperature, 4);
    memcpy(&payload[4], &humidity, 4);

    if (!ha.isRegistered()) {
        ha.registerWithGateway();
        publishChannel = ha.publishChannel("temperature.desk", temperatureTransformId);
    }

    ha.publish(publishChannel, payload, 12);

    if (!ha.isRegistered()) {
        ha.registerWithGateway();
        publishChannel = ha.publishChannel("temperature.desk", temperatureTransformId);
    }

    delay(100);
}

void powerDown() {
    radio.stopListening();
    radio.powerDown();
    LowPower.powerDown(SLEEP_8S, ADC_OFF, BOD_OFF);
    radio.powerUp();
    radio.startListening();
    numberOfSleepPeriodsSinceLastLog += 1;
}
