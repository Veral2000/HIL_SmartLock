This repo is for the Hardware in Loop framework implementation for the Smart Lock, We are making the device(HIL) for the smart lock to help OEM's for to test Interfaces (RFID, Magnetic Stripe and Keypad). 

This Repo consits of below files:
  1. HIL_SmartLock.py - Python Script - this will run as a service in the smart lock, where it supports the interfaces like RFID, Keypad and MSR.
  2. service file - Service file makes the python file to run as a service, where we have to keep this file under systemd folder and enable and start this service.  
