import serial
import time

x = 0

ser=serial.Serial("/dev/ttyUSB0", 9600)
ser.baudrate=9600

while x < 1000:
    p = read_ser=ser.readline()
    p = p.decode('utf-8')
    print(p)
    x = x + 1
    


