*** Settings ***
Library           CustomKeywords.py

*** Test Cases ***

CORRECT MSR TEST
    # Send data to MCU (through the helper method)
    Send To MCU    {"mode": "msr", "data": "%pawan?;123456789?"}
    # Wait for processed data (through the helper method)
    ${response}=    Wait For Data    timeout=15

    # Check if response matches the expected output
    Run Keyword If    ${response} == {"led": "green","lock":"Unlocked"}   Log    The input matches ${response}. Test passed!
    ...               ELSE    Fail    The input does not match ${response}. Test failed!

    Sleep    5s


WRONG MSR TEST
    # Send data to MCU (through the helper method)
    Send To MCU    {"mode": "msr", "data": "%pawan?;12345678?"}

    # Wait for processed data (through the helper method)
    ${response}=    Wait For Data    timeout=5

    # Check if response matches the expected output
    Run Keyword If    ${response} == {"led": "red"}   Log    The input matches ${response}. Test passed!
    ...               ELSE    Fail    The input does not match ${response}. Test failed!

    Sleep  5s 

WRONG KEYPAD TEST
     # Send data to MCU (through the helper method)
     Send To MCU    {"mode": "keypad", "data": [3,5,5,3]}

     # Wait for processed data (through the helper method)
     ${response}=    Wait For Data    timeout=7

     # Check if response matches the expected output
     Run Keyword If    ${response} == {"led": "red"}   Log  The input matches ${response}. Test passed!
     ...               ELSE    Fail    The input does not match ${response}. Test failed!
    
    Sleep    7s

CORRECT KEYPAD TEST
     # Send data to MCU (through the helper method)
     Send To MCU    {"mode": "keypad", "data": [5,7,5,7]}

     # Wait for processed data (through the helper method)
     ${response}=    Wait For Data    timeout=15

     # Check if response matches the expected output
     Run Keyword If    ${response} == {"led": "green","lock":"Unlocked"}    Log    The input matches ${response}. Test passed!
     ...               ELSE    Fail    The input does not match ${response}. Test failed!
     
    Sleep  10s

CORRECT RFID TEST
    [Tags]   RFID CHANNEL 1
    # Send data to MCU (through the helper method)
    Send To MCU    {"mode": "rfid", "data": 0}

    # Wait for processed data (through the helper method)
    ${response}=    Wait For Data    timeout=15

    # Check if response matches the expected output
    Run Keyword If    ${response} == {"led": "green","lock":"Unlocked"}    Log    The input matches ${response}. Test passed!
    ...               ELSE    Fail    The input does not match ${response}. Test failed!
    
    Sleep  5s


# WRONG RFID TEST
#     # Send data to MCU (through the helper method)
#     Send To MCU    {"mode": "rfid", "data": 1}

#     # Wait for processed data (through the helper method)
#     ${response}=    Wait For Data    timeout=7

#     # Check if response matches the expected output
#     Run Keyword If    ${response} == {"led": "green","lock":"Unlocked"}   Log    The input matches ${response}. Test passed!
#     ...               ELSE    Fail    The input does not match ${response}. Test failed!
    
#     Send To MCU    {"mode": "rfid", "data": 3}

#     Sleep  5s