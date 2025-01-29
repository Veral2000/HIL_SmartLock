import os
import threading
import time
import RPi.GPIO as GPIO
from time import sleep
from mfrc522 import SimpleMFRC522


#    semantic versioning
#
#    MAJOR version when you make incompatible API changes
#    MINOR version when you add functionality in a backward compatible manner
#    PATCH version when you make backward compatible bug fixes

MAJOR = 1
MINOR = 2
PATCH = 2

#


# Pins Assignment as per the Raspberry Pi Board Pins.
BUZZER_PIN = 32
RELAY_PIN = 40
LED_R = 8
LED_G = 12
LED_B = 10

#MultiThreading Events
pause_event = threading.Event()
pause_event.set()  

#GPIO Set Mode for the assigned pins
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(True)

#GPIO Setup 
#Relay
GPIO.setup(RELAY_PIN, GPIO.OUT)
#RGB LED
GPIO.setup(LED_R, GPIO.OUT)
GPIO.setup(LED_G, GPIO.OUT)
GPIO.setup(LED_B, GPIO.OUT)
#Buzzer
GPIO.setup(BUZZER_PIN,GPIO.OUT)
#GPIO Setup END

#RGB LED PWM Enable at 100Hz Frequency
pwm_red = GPIO.PWM(LED_R, 100)   # 100Hz frequency
pwm_green = GPIO.PWM(LED_B, 100)
pwm_blue = GPIO.PWM(LED_G, 100)

#PWM Start
pwm_red.start(0)
pwm_green.start(0)
pwm_blue.start(0)

#Buzzer PWM Initiate
pwm = GPIO.PWM(BUZZER_PIN, 1000)

#PWN Set Color
def set_color(red_value, green_value, blue_value):
    pwm_red.ChangeDutyCycle(red_value)
    pwm_green.ChangeDutyCycle(green_value)
    pwm_blue.ChangeDutyCycle(blue_value)

#Lock Credentials for Access {MSC, Keypad, RFID}
lock_access_data = [
    ";123456789?=123456789?",
    ['4','7','8','5'],
    "312334224"
]

#initiating RFID IC (SPI)
reader = SimpleMFRC522()
#key_code = []

# Utility function to set GPIO mode only if not already set
def setup_gpio_mode():
    try:
        # Attempt to set GPIO mode if not already set
        GPIO.setmode(GPIO.BOARD)
    except ValueError:
        # GPIO mode is already set, ignore this error
        pass

# process_data():- This function is used for processing the data coming from the Lock Interfaces, when user privudes input in any of the interface
def process_data(data):
    if data in lock_access_data:
        print(data)
        set_color(0, 0, 100)
        access_granted()
        print("Access Granted")
        GPIO.output(RELAY_PIN,0)
        sleep(5)
        set_color(0, 0, 0)
        GPIO.output(RELAY_PIN,1)
    else:
        print("Access Denied")
        print(data)  
        GPIO.output(LED_R,0)
        set_color(100, 0, 0)
        access_denied()
        sleep(2)
        set_color(0, 0, 0)

#play_tone():- This function is used for Buzzer, Parameters: Frequency and Duration.
def play_tone(frequency, duration):
    """
    Play a tone on the passive buzzer.

    :param frequency: Frequency of the tone in Hz
    :param duration: Duration of the tone in seconds
    """
    pwm.ChangeFrequency(frequency)  # Set the frequency
    pwm.start(50)  # 50% duty cycle to produce sound
    time.sleep(duration)  # Wait for the tone to play
    pwm.stop()  # Stop the buzzer after playing

#access_granted():- This function is used for Buzzer when the access is granted
def access_granted():
    """
    Play the 'Access Granted' sound.
    """
    print("Access Granted!")
    play_tone(523, 0.2)  # C5
    time.sleep(0.1)
    play_tone(659, 0.2)  # E5
    time.sleep(0.1)
    play_tone(784, 0.2)  # G5

#access_denied():- This function is used for Buzzer when the access is denied
def access_denied():
    """
    Play the 'Access Denied' sound.
    """
    print("Access Denied!")
    play_tone(784, 0.2)  # G5
    time.sleep(0.1)
    play_tone(659, 0.2)  # E5
    time.sleep(0.1)
    play_tone(523, 0.2)  # C5
    time.sleep(0.1)
    play_tone(440, 0.4)  # A4 (longer tone for a harsher effect)


            
# MSR Reader code (from file 1)
keycode_map = {
    0x1E: '1', 0x1F: '2', 0x20: '3', 0x21: '4', 0x22: '5', 0x23: '6', 
    0x24: '7', 0x25: '8', 0x26: '9', 0x27: '0',
    0x04: 'A', 0x05: 'B', 0x06: 'C', 0x07: 'D', 0x08: 'E', 0x09: 'F',
    0x0A: 'G', 0x0B: 'H', 0x0C: 'I', 0x0D: 'J', 0x0E: 'K', 0x0F: 'L',
    0x10: 'M', 0x11: 'N', 0x12: 'O', 0x13: 'P', 0x14: 'Q', 0x15: 'R',
    0x16: 'S', 0x17: 'T', 0x18: 'U', 0x19: 'V', 0x1A: 'W', 0x1B: 'X',
    0x2C: ' ', 0x2D: '-', 0x2E: '=', 0x2F: '[', 0x30: ']', 0x31: '\\',
    0x39: 'CapsLock', 0x2B: 'TAB', 0x1C: 'Enter',
    0x3D: '%', 0x3E: '^', 0x3F: '/', 0x40: ';', 0x38: '?', 0x33: ';'
}

#convert byte to string
def convert_byte_to_string(byte_data):
    string_output = []
    for byte_sequence in byte_data:
        if byte_sequence[0] == 0x20:  # Skip processing for the whole sequence if first byte is 0x20
            if byte_sequence[2] == 0x22:
                string_output.append("%")
            elif byte_sequence[2] == 0x23:
                string_output.append("^")
            else:
                string_output.append(keycode_map[byte_sequence[2]])  # Process the third byte
            continue
        for byte in byte_sequence:
            if byte != 0:
                if byte in keycode_map:
                    string_output.append(keycode_map[byte])
    return ''.join(string_output)

#read MSR
def read_msr(fd, byte_data, lock):
    buffer_size = 8
    while True:
        pause_event.wait() 
        data_chunk = os.read(fd, buffer_size)
        if data_chunk:
            with lock:
                byte_data.append(data_chunk)

#process msr data
def process_msr_data(byte_data, lock):
    while True:
        pause_event.wait() 
        time.sleep(2)
        with lock:
            if byte_data:
                resulting_string = convert_byte_to_string(byte_data)
                count = resulting_string.count('?')
                if count > 2:
                    resulting_string = resulting_string.replace('?', '/', 1)
                process_data(resulting_string)
                byte_data.clear()

# Keypad Code (from file 2)
class keypad():
    KEYPAD = [[1, 2, 3], [4, 5, 6], [7, 8, 9], ["*", 0, "#"]]
    ROW = [31, 38, 36, 35]
    COLUMN = [33, 29, 37]

    def __init__(self):
        setup_gpio_mode()  # Ensure GPIO mode is set only once
        self.last_key_time = 0  # To track the last key press time
        self.debounce_time = 0.2  # 200 ms debounce time

    def getKey(self):
        current_time = time.time()
        
        # Check if enough time has passed since the last key press
        if current_time - self.last_key_time < self.debounce_time:
            return None

        for j in range(len(self.COLUMN)):
            GPIO.setup(self.COLUMN[j], GPIO.OUT)
            GPIO.output(self.COLUMN[j], GPIO.LOW)
        
        for i in range(len(self.ROW)):
            GPIO.setup(self.ROW[i], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        rowVal = -1
        for i in range(len(self.ROW)):
            tmpRead = GPIO.input(self.ROW[i])
            if tmpRead == 0:
                rowVal = i
                break
        
        if rowVal < 0 or rowVal > 3:
            self.exit()
            return None
        
        for j in range(len(self.COLUMN)):
            GPIO.setup(self.COLUMN[j], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        GPIO.setup(self.ROW[rowVal], GPIO.OUT)
        GPIO.output(self.ROW[rowVal], GPIO.HIGH)
        
        colVal = -1
        for j in range(len(self.COLUMN)):
            tmpRead = GPIO.input(self.COLUMN[j])
            if tmpRead == 1:
                colVal = j
                break
        
        if colVal < 0 or colVal > 2:
            self.exit()
            return None
        
        self.last_key_time = current_time  # Update the last key press time
        self.exit()
        return self.KEYPAD[rowVal][colVal]
        
    def exit(self):
        for i in range(len(self.ROW)):
            GPIO.setup(self.ROW[i], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        for j in range(len(self.COLUMN)):
            GPIO.setup(self.COLUMN[j], GPIO.IN, pull_up_down=GPIO.PUD_UP)

#keypad digit display
def digit_return():
    kp = keypad()
    global key_code
    while True:
        key = kp.getKey()
        if key is not None:
            if key == '#':    
                set_color(100, 0, 30)
                key_code.clear()  # Clear previous code
                print("Enter 4-digit code:")
                pause_event.clear() 
            elif len(key_code) < 4:
                key_code.append(str(key))
                if len(key_code) == 4:
                    set_color(0, 0, 0)
                    process_data(key_code)

                    pause_event.set()
        time.sleep(0.05)
        

# RFID Reader code (from file 3)
def listen_rfid():
    while True:
        pause_event.wait()
        id, data = reader.read_no_block()
        if data:
            process_data(data.strip())
        time.sleep(0.2)  # Add a short delay to reduce CPU usage


# Main function to run all threads
def main():
    GPIO.setwarnings(False)
    setup_gpio_mode()

    # MSR Setup
    device_path = '/dev/hidraw0'
    fd = os.open(device_path, os.O_RDWR)
    byte_data = []
    lock = threading.Lock()

    # Create threads
    threads = [
        threading.Thread(target=digit_return),
        threading.Thread(target=read_msr, args=(fd, byte_data, lock)),
        threading.Thread(target=process_msr_data, args=(byte_data, lock)),
        threading.Thread(target=listen_rfid)
    ]

    # Start threads
    for thread in threads:
        thread.start()

    # Wait for threads to finish (they likely won't, as they're continuous listeners)
    for thread in threads:
        thread.join()

    os.close(fd)

if __name__ == "__main__":
    main()

