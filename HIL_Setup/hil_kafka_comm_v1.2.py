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

# Load configuration from config.json
with open("config.json", "r") as f:
    CONFIG = json.load(f)

# Serial setup
serial_port = CONFIG["serial"]["port"]
baud_rate = CONFIG["serial"]["baudrate"]
mcu = serial.Serial(serial_port, baud_rate, timeout=2)
mcu.timeout = 2

# GPIO Pin Setup
gpio_conf = CONFIG["gpio"]
relay_pins = gpio_conf["relays"]
rfid_pins = gpio_conf["rfid_pins"]
motor_conf = gpio_conf["motor_pwm"]
limit_conf = gpio_conf["limit_switch"]

for pin in relay_pins + rfid_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, 1)

RPWM = motor_conf["RPWM"]
LPWM = motor_conf["LPWM"]
R_EN = motor_conf["R_EN"]
L_EN = motor_conf["L_EN"]

GPIO.setup(RPWM, GPIO.OUT)
GPIO.setup(LPWM, GPIO.OUT)
GPIO.setup(R_EN, GPIO.OUT)
GPIO.setup(L_EN, GPIO.OUT)
GPIO.output(R_EN, GPIO.HIGH)
GPIO.output(L_EN, GPIO.HIGH)

LIMIT_SWITCH_PIN = limit_conf["pin"]
LIMIT_SWITCH_HIGH = limit_conf["high_pin"]
GPIO.setup(LIMIT_SWITCH_HIGH, GPIO.OUT)
GPIO.output(LIMIT_SWITCH_HIGH, GPIO.HIGH)
GPIO.setup(LIMIT_SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

pwm_r = GPIO.PWM(RPWM, 1000)
pwm_l = GPIO.PWM(LPWM, 1000)
pwm_r.start(0)
pwm_l.start(0)

# Kafka Setup
broker = CONFIG["kafka"]["broker"]
send_topic = CONFIG["kafka"]["send_topic"]
receive_topic = CONFIG["kafka"]["receive_topic"]

consumer = KafkaConsumer(
    send_topic,
    bootstrap_servers=broker,
    auto_offset_reset='latest',
    enable_auto_commit=True,
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

producer = KafkaProducer(
    bootstrap_servers=broker,
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

# Sensor Setup
sensor_conf = CONFIG["sensor"]
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_tcs34725.TCS34725(i2c)
sensor.integration_time = sensor_conf["integration_time"]
sensor.gain = sensor_conf["gain"]
sensor.led = sensor_conf["led"]

r = g = b = c = 0
rgb_lock = threading.Lock()
LIMIT_SWITCH_PRESSED = False

def limit_switch_callback(channel):
    global LIMIT_SWITCH_PRESSED
    LIMIT_SWITCH_PRESSED = GPIO.input(LIMIT_SWITCH_PIN) == GPIO.LOW

GPIO.add_event_detect(LIMIT_SWITCH_PIN, GPIO.BOTH, callback=limit_switch_callback, bouncetime=200)

def move_forward(speed=50):
    pwm_r.ChangeDutyCycle(speed)
    pwm_l.ChangeDutyCycle(0)

def move_backward(speed=50):
    pwm_r.ChangeDutyCycle(0)
    pwm_l.ChangeDutyCycle(speed)

def stop_motor():
    pwm_r.ChangeDutyCycle(0)
    pwm_l.ChangeDutyCycle(0)

def read_color():
    global r, g, b, c
    thresholds = CONFIG["color_thresholds"]
    while True:
        r_raw, g_raw, b_raw, c_raw = sensor.color_raw
        with rgb_lock:
            r, g, b, c = r_raw, g_raw, b_raw, c_raw

        if r > thresholds["red"]["r_min"] and g < thresholds["red"]["g_max"] and b < thresholds["red"]["b_max"]:
            producer.send(receive_topic, value={"led": "red"})
        elif r < thresholds["green"]["r_max"] and g > thresholds["green"]["g_min"] and b > thresholds["green"]["b_min"]:
            move_backward(70)
            time.sleep(1)
            stop_motor()
            move_forward(70)
            time.sleep(5)
            if LIMIT_SWITCH_PRESSED:
                producer.send(receive_topic, value={"led": "green", "lock": "Unlocked"})
            stop_motor()
            move_backward(70)
            time.sleep(5)
            stop_motor()
        time.sleep(1)

def calculate_crc32(data):
    return zlib.crc32(data.encode('utf-8'))

def send_data_frame(seq, cmd, data):
    frame = (
        (1).to_bytes(1, 'big') +
        seq.to_bytes(1, 'big') +
        cmd.to_bytes(1, 'big') +
        len(data).to_bytes(2, 'big') +
        data.encode('utf-8') +
        calculate_crc32(data).to_bytes(4, 'big') +
        (0).to_bytes(1, 'big')
    )
    mcu.write(frame)

def receive_data_frame():
    if mcu.read(1) == b'\x01':
        length = int.from_bytes(mcu.read(2), 'big')
        data = mcu.read(length)
        crc32 = int.from_bytes(mcu.read(4), 'big')
        if mcu.read(1) == b'\x00' and zlib.crc32(data) == crc32:
            return data.decode('utf-8')
    return None

def consume_data():
    seq_num = 0
    for msg in consumer:
        msg_json = msg.value if isinstance(msg.value, dict) else json.loads(msg.value)

        if 'msr' in msg_json.values():
            send_data_frame(seq_num, 2, msg_json['data'])
            mcu.flushInput()
            receive_data_frame()
            seq_num += 1

        elif 'rfid' in msg_json.values():
            bin_val = format(msg_json['data'], '03b')
            for i, pin in enumerate(rfid_pins):
                GPIO.output(pin, int(bin_val[i]))
            time.sleep(4)
            for pin in rfid_pins:
                GPIO.output(pin, 1)

        elif 'keypad' in msg_json.values():
            GPIO.output(relay_pins[2], 0)
            time.sleep(0.2)
            GPIO.output(relay_pins[2], 1)
            time.sleep(0.5)

            for digit in msg_json['data']:
                if digit == 5:
                    idx = 0
                elif digit == 3:
                    idx = 1
                elif digit == 7:
                    idx = 3
                else:
                    continue
                GPIO.output(relay_pins[idx], 0)
                time.sleep(0.2)
                GPIO.output(relay_pins[idx], 1)
                time.sleep(0.5)

# Start Threads
threading.Thread(target=consume_data).start()
threading.Thread(target=read_color).start()
