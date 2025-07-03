# Raspberry Pi Kafka-MCU RGB Sensor Bridge

This Python script enables a Raspberry Pi to:
- Send MSR/RFID data from Kafka to an MCU via UART
- Read RGB values from a TCS34725 sensor
- Publish LED results (`red`/`green`) to Kafka

## Requirements

- Raspberry Pi (with I2C, UART, GPIO)
- TCS34725 color sensor
- Kafka server at IP Address (e.g.`192.168.210.186:9092`)
- Python 3.7+

## Install

```bash
sudo apt update
sudo apt install python3-pip
pip3 install -r requirements.txt
