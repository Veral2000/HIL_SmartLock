from kafka import KafkaConsumer

# Kafka configuration
topic = "myTopic"  # Replace with your actual topic name
bootstrap_servers = "192.168.210.186:9092"  # Change this to your Kafka broker

# Create Kafka Consumer
consumer = KafkaConsumer(
    topic,
    bootstrap_servers=bootstrap_servers,
    group_id="my-consumer-group",  # Consumer group ID
    auto_offset_reset="earliest",  # Start from the beginning if no offset is stored
    enable_auto_commit=True
)

print(f"Subscribed to topic: {topic}")

try:
    for message in consumer:
        print(f"Received message: {message.value.decode('utf-8')}")
except KeyboardInterrupt:
    print("\nClosing consumer...")
finally:
    consumer.close()
