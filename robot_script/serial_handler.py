import time
import serial
import logging
from kafka import KafkaProducer, KafkaConsumer
import threading  # To use threading for parallel tasks
import json

logging.basicConfig(level=logging.INFO)

class SerialHandler:
    def __init__(self, port="COM4", baudrate=9600, timeout=1, kafka_broker='192.168.210.186:9092'):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = serial.Serial(port, baudrate, timeout=timeout)

        self.kafka_broker = kafka_broker
        self.send_topic = "send_data_to_mcu"  # Topic to send data to the MCU
        self.receive_topic = "get_deta_from_mcu"  # Topic to receive data from the MCU
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_broker,
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        self.consumer = KafkaConsumer(
            self.send_topic,
            bootstrap_servers=kafka_broker,
            auto_offset_reset='latest',
            enable_auto_commit=False,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        logging.info("Initialized Kafka Producer and Consumer")

    def send_data_to_mcu(self, data):
        try:
            self.ser.write(data.encode('utf-8'))  # Send data to MCU
            logging.info(f"Sent to MCU: {data}")
        except Exception as e:
            logging.error(f"Error sending data to MCU: {e}")

    def receive_data_from_mcu(self):
        try:
            raw_data = self.ser.read_until(b'\n')  # Read until newline
            if raw_data:
                decoded_data = raw_data.decode('utf-8').strip()
                logging.info(f"Received from MCU: {decoded_data}")
                self.producer.send(self.receive_topic, value=decoded_data)
                self.producer.flush()
                logging.info(f"Published to Kafka topic {self.receive_topic}: {decoded_data}")
        except Exception as e:
            logging.error(f"Error receiving data from MCU: {e}")

    def process_kafka_messages(self):
        try:
            for message in self.consumer:
                kafka_data = message.value
                logging.info(f"Received from Kafka: {kafka_data}")
                self.send_data_to_mcu(kafka_data)
        except Exception as e:
            logging.error(f"Error processing Kafka messages: {e}")

    def close(self):
        self.ser.close()
        self.producer.close()
        self.consumer.close()
        logging.info("Closed serial port and Kafka connections")

# Main loop
if __name__ == "__main__":
    serial_handler = SerialHandler(port="COM4", baudrate=9600, kafka_broker="192.168.210.186:9092")
    try:
        # Start Kafka message processing in a separate thread
        kafka_thread = threading.Thread(target=serial_handler.process_kafka_messages)
        kafka_thread.daemon = True  # Allow the thread to exit when the main program exits
        kafka_thread.start()

        while True:
            serial_handler.receive_data_from_mcu()  # Check for data from MCU
             # Placeholder for checking messages from Kafka
            # time.sleep(0.1)  # Add a short delay to prevent high CPU usage
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    finally:
        serial_handler.close()
