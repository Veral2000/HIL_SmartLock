import logging
from kafka import KafkaProducer, KafkaConsumer
from collections import namedtuple
import json

logging.basicConfig(level=logging.INFO)

# Kafka resource placeholders
kafka_producer = None
kafka_consumer = None

class CustomKeywords:
    def __init__(self, kafka_broker='192.168.210.186:9092', send_topic='send_data_to_mcu', receive_topic='get_deta_from_mcu'):
        global kafka_producer, kafka_consumer

        self.send_topic = send_topic
        self.receive_topic = receive_topic

        if kafka_producer is None:
            kafka_producer = KafkaProducer(
                bootstrap_servers=kafka_broker,
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            logging.info(f"Kafka producer initialized for topic: {send_topic}")

        if kafka_consumer is None:
            kafka_consumer = KafkaConsumer(
                receive_topic,
                bootstrap_servers=kafka_broker,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            logging.info(f"Kafka consumer initialized for topic: {receive_topic}")

    def send_to_mcu(self, data):
        global kafka_producer
        try:
            kafka_producer.send(self.send_topic, value=data)
            kafka_producer.flush()
            logging.info(f"Data sent to {self.send_topic}: {data}")
        except Exception as e:
            logging.error(f"Error sending data: {e}")
            raise

    def wait_for_data(self, timeout=5):
        global kafka_consumer
        try:
            raw_messages = kafka_consumer.poll(timeout_ms=timeout * 1000)
            for records in raw_messages.values():
                if records:
                    latest_record = records[-1]
                    logging.info(f"Received data: {latest_record.value}")
                    return latest_record.value
        except Exception as e:
            logging.warning(f"Timeout or error receiving data: {e}")
        return None

    def close(self):
        global kafka_producer, kafka_consumer
        if kafka_producer:
            kafka_producer.close()
            logging.info("Kafka producer closed")
        if kafka_consumer:
            kafka_consumer.close()
            logging.info("Kafka consumer closed")


# ==== Wrapper functions for Robot Framework ====

# These are required for Robot to access them directly

_keywords = CustomKeywords()

def send_to_mcu(data):
    """Robot keyword: Send data to MCU via Kafka"""
    _keywords.send_to_mcu(eval(data) if isinstance(data, str) else data)

def wait_for_data(timeout=5):
    """Robot keyword: Wait for MCU response"""
    return _keywords.wait_for_data(timeout=int(timeout))

def close_kafka():
    """Robot keyword: Close Kafka resources"""
    _keywords.close()
