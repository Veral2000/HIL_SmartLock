#This is the older version of the HIL communication code which works without config, here all the configuration is done in variables it self.
#Recommended to use v1.2 using config.json

import serial
import time
import zlib
from kafka import KafkaConsumer, KafkaProducer
import json
import threading
import board
import busio
import adafruit_tcs34725
import RPi.GPIO as GPIO


# Serial setup
serial_port = '/dev/ttyUSB0'
baud_rate = 9600
seq_num = 0
cmd_num = 2

mcu = serial.Serial(serial_port, baud_rate, timeout=2)
mcu.timeout = 2

relay_pin1 = 17
relay_pin2 = 18
relay_pin3 = 27
relay_pin4 = 22

rf_pin1 =23
rf_pin2 = 24
rf_pin3 =25

RPWM = 13  # Right PWM (Forward)
LPWM = 19  # Left PWM (Reverse)
R_EN = 26  # Right Enable
L_EN = 21  # Left Enable


LIMIT_SWITCH_PIN = 12  # Use BCM GPIO pin number
LIMIT_SWITCH_HIGH = 16

GPIO.setup(LIMIT_SWITCH_HIGH, GPIO.OUT)
GPIO.output(LIMIT_SWITCH_HIGH, GPIO.HIGH)

GPIO.setup(LIMIT_SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Enable pull-up resistor

GPIO.setup(RPWM, GPIO.OUT)
GPIO.setup(LPWM, GPIO.OUT)
GPIO.setup(R_EN, GPIO.OUT)
GPIO.setup(L_EN, GPIO.OUT)

GPIO.output(R_EN, GPIO.HIGH)
GPIO.output(L_EN, GPIO.HIGH)

pwm_r = GPIO.PWM(RPWM, 1000)
pwm_l = GPIO.PWM(LPWM, 1000)
pwm_r.start(0)  # Start with 0% duty cycle
pwm_l.start(0)


GPIO.setup(relay_pin1, GPIO.OUT)
GPIO.setup(relay_pin2, GPIO.OUT)
GPIO.setup(relay_pin3, GPIO.OUT)
GPIO.setup(relay_pin4, GPIO.OUT)

GPIO.setup(rf_pin1, GPIO.OUT)
GPIO.setup(rf_pin2, GPIO.OUT)
GPIO.setup(rf_pin3, GPIO.OUT)

GPIO.output(rf_pin1,1)
GPIO.output(rf_pin2,1)
GPIO.output(rf_pin3,1)

# RGB values
r = 0
g = 0
b = 0
c = 0

# Create a lock for synchronizing access to RGB values
rgb_lock = threading.Lock()

# Kafka Consumer setup
consumer = KafkaConsumer(
    'send_data_to_mcu',  # Replace with your Kafka topic
    bootstrap_servers='192.168.137.89:9092',
    auto_offset_reset='latest',  # Start from the earliest message
    enable_auto_commit=True,
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Kafka Producer setup
producer = KafkaProducer(
    bootstrap_servers='192.168.137.89:9092',
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

# Create I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create a sensor object
sensor = adafruit_tcs34725.TCS34725(i2c)

# Set sensor integration time (optional, default is 2.4ms)
sensor.integration_time = 50  # You can set it between 2.4ms and 614ms

# Set gain (optional, default is 1x)
# sensor.gain = 16  # Options: 1x, 4x, 16x, 60x

# Enable LED (optional)
sensor.led = True

LIMIT_SWITCH_PRESSED = False

def limit_switch_callback(channel):
    global LIMIT_SWITCH_PRESSED
    if GPIO.input(LIMIT_SWITCH_PIN) == GPIO.LOW:
        print("Limit switch pressed!")
        LIMIT_SWITCH_PRESSED = True
    else:
        print("Limit switch released!")
        LIMIT_SWITCH_PRESSED = False

GPIO.add_event_detect(LIMIT_SWITCH_PIN, GPIO.BOTH, callback=limit_switch_callback, bouncetime=200)

def move_forward(speed=50):
    """Move forward with given speed (0-100%)."""
    pwm_r.ChangeDutyCycle(speed)
    pwm_l.ChangeDutyCycle(0)

def move_backward(speed=50):
    """Move backward with given speed (0-100%)."""
    pwm_r.ChangeDutyCycle(0)
    pwm_l.ChangeDutyCycle(speed)

def stop_motor():
    """Stop motor."""
    pwm_r.ChangeDutyCycle(0)
    pwm_l.ChangeDutyCycle(0)

#Function to get color data
def read_color():
    global r, g, b, c
    while True:
        # Read the color values
        r_raw, g_raw, b_raw, c_raw = sensor.color_raw
        with rgb_lock:  # Acquire the lock before updating RGB values
            r, g, b, c = r_raw, g_raw, b_raw, c_raw
        print(f"Red: {r}, Green: {g}, Blue: {b}")
        
        topic_to_publish = 'get_deta_from_mcu' 
    
        if r > 1500 and g < 400 and b < 500:
            data_to_publish = {"led": "red"}  # Replace with actual data to publish
            producer.send(topic_to_publish, value=data_to_publish)  # Send data to Kafka
            print(f"published {data_to_publish}")
            time.sleep(2)
            
        elif r<428 and g>1400 and b >250:

            move_backward(70)
            time.sleep(1)
            stop_motor()
           

            move_forward(70)
            time.sleep(5)

            print(f"LIMIT_SWITCH_PRESSED {LIMIT_SWITCH_PRESSED}")
            
            if LIMIT_SWITCH_PRESSED:
            
                data_to_publish = {"led": "green","lock":"Unlocked"}  # Replace with actual data to publish
                producer.send(topic_to_publish, value=data_to_publish)  # Send data to Kafka
                print(f"published {data_to_publish}")

            stop_motor()
            
            print("Moving Forward")

            move_backward(70)
            time.sleep(5)
            
            stop_motor()

        time.sleep(1)

def calculate_crc32(data):
    crc32_value = zlib.crc32(data.encode('utf-8'))
    return crc32_value

def send_data_frame(seq, cmd, data):
    start_byte = (1).to_bytes(1, byteorder='big')
    length_bytes = len(data).to_bytes(2, byteorder='big')
    end_byte = (0).to_bytes(1, byteorder='big')
    crc32_value = calculate_crc32(data).to_bytes(4, byteorder='big')

    # Create the data frame
    data_frame = start_byte + seq.to_bytes(1, byteorder='big') + cmd.to_bytes(
        1, byteorder='big') + length_bytes + data.encode('utf-8') + crc32_value + end_byte

    mcu.write(data_frame)
    print(f"Sent data: {data}")
    


def receive_data_frame():
    start_byte = mcu.read(1)
    if start_byte == b'\x01':  # Check for start byte
        length_bytes = mcu.read(2)
        length = int.from_bytes(length_bytes, byteorder='big')
        data_received = mcu.read(length)
        crc32_bytes = mcu.read(4)
        end_byte = mcu.read(1)
        
        # Validate CRC32 and end byte
        calculated_crc32 = zlib.crc32(data_received) & 0xFFFFFFFF
        received_crc32 = int.from_bytes(crc32_bytes, byteorder='big')

        if received_crc32 == calculated_crc32 and end_byte == b'\x00':
            print(f"Received data: {data_received.decode('utf-8')}")
            return "successful"
    
    return None

def consume_data_from_kafka():
    global seq_num
    for message in consumer:
        # Assuming the Kafka message contains the data as a JSON key-value pair

        if isinstance(message.value, str):
            try:
                message_json = json.loads(message.value)  # Convert JSON string to dictionary
            except json.JSONDecodeError:
                print("Error: Failed to decode JSON.")
                continue  # Skip this message
        elif isinstance(message.value, dict):
            message_json = message.value

        print(f"Received data from Kafka: {message_json}")

        
        # print(f"dsdsd {message.value['fff']}")
        if 'msr' in message_json.values():
            data_to_send = message_json['data']  # Assuming the key in the message is 'data'

        # Send the data received from Kafka to the MCU
            send_data_frame(seq_num, cmd_num, data_to_send)
            mcu.flushInput()  # Clear the buffer
            response_frame = receive_data_frame()  # Optionally handle response if needed
            seq_num += 1  # Increment sequence number after each send
            

        elif 'rfid' in message_json.values():
           
            
            bin_value = format(message_json['data'], '03b') 
            print (bin_value)
            GPIO.output(rf_pin1, int(bin_value[0]))  # Set pin1 (MSB)
            GPIO.output(rf_pin2, int(bin_value[1]))  # Set pin2
            GPIO.output(rf_pin3, int(bin_value[2])) 
            # publish_data()
            time.sleep(4)
            GPIO.output(rf_pin1,1)
            GPIO.output(rf_pin2,1)
            GPIO.output(rf_pin3,1)
        
        elif 'keypad' in message_json.values():
            temp = message_json['data']
            print(type(temp[0]))
            GPIO.output(relay_pin3,0)
            time.sleep(0.2)
            GPIO.output(relay_pin3,1)
            time.sleep(0.5)
            
            for i in temp:
	
                if(i == 5):
                    GPIO.output(relay_pin1,0)
                    time.sleep(0.2)
                    GPIO.output(relay_pin1,1)
                    time.sleep(0.5)
                    print("pressed 5")
                elif(i == 3):
                    GPIO.output(relay_pin2,0)
                    time.sleep(0.2)
                    GPIO.output(relay_pin2,1)
                    time.sleep(0.5)
                    print("pressed 3")
                elif(i == 7):
                    GPIO.output(relay_pin4,0)
                    time.sleep(0.2)
                    GPIO.output(relay_pin4,1)
                    time.sleep(0.5)
                    print("pressed 7")
                
def publish_data():
    global r, g, b, c
    while True:
        topic_to_publish = 'get_deta_from_mcu'  # Replace with your desired Kafka topic
        with rgb_lock:  # Acquire the lock before reading RGB values
            # Debugging output to check current RGB values
            
            if r > 16200 and g < 2000 and b < 2500:
                data_to_publish = {"led": "red"}  # Replace with actual data to publish
                # producer.send(topic_to_publish, value=data_to_publish)  # Send data to Kafka
                # print(f"published {data_to_publish}")
                r=0
                g=0
                b=0
                time.sleep(2)  # Sleep for some time before publishing again # Sleep for some time before publishing again

            elif r<4280 and g>19000 and b >8000:
                data_to_publish = {"led": "green"}  # Replace with actual data to publish
                # producer.send(topic_to_publish, value=data_to_publish)  # Send data to Kafka
                # print(f"published {data_to_publish}")
                r=0
                g=0
                b=0
                time.sleep(10)  # Sleep for some time before publishing again # Sleep for some time before publishing again               
        # time.sleep(0.5)
# Start the Kafka consumer in a separate thread
consumer_thread = threading.Thread(target=consume_data_from_kafka)
consumer_thread.start()

# Start the data publishing thread
# publish_thread = threading.Thread(target=publish_data)
# publish_thread.start()

# Start the color sensor reading thread
color_sensor = threading.Thread(target=read_color)
color_sensor.start()

# Optionally join threads if you want to wait for them to finish
color_sensor.join()
consumer_thread.join()
# publish_thread.join()

mcu.close()
