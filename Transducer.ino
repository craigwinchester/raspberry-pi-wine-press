/* This example demonstrates how to take a standard 3-wire pressure transducer
 *  and read the analog signal, then convert the signal to a readable output and
 *  display it onto an LCD screen.
 *  
 *  Contact Tyler at tylerovens@me.com if you have any questions
 */

 #include "Wire.h" //allows communication over i2c devices

 const int pressureInput = A0; //select the analog input pin for the pressure transducer
 const int pressureZero = 96.256; //analog reading of pressure transducer at 0psi 102.4=old number
 const int pressureMax = 921.6; //analog reading of pressure transducer at 30psi
 const int pressuretransducermaxPSI = 30; //psi value of transducer being used
 const int baudRate = 9600; //constant integer to set the baud rate for serial monitor
 const int sensorreadDelay = 250; //constant integer to set the sensor read delay in milliseconds
 
 float pressureValue = 0; //variable to store the value coming from the pressure transducer
 float pressureValueBAR = 0;
 float voltage = 0;
 
 int pressureInt;
 
 void setup() //setup routine, runs once when system turned on or reset
 {
   Serial.begin(baudRate); //initializes serial communication at set baud rate bits per second
   
 }
 
 void loop() //loop routine runs over and over again forever
 {
   pressureValue = analogRead(pressureInput); //reads value from input pin and assigns to variable
   voltage = (pressureValue*5.0)/1024.0;
   //Serial.print(voltage, 4);
   //Serial.println(" volts");
   pressureValue = ((pressureValue-pressureZero)*pressuretransducermaxPSI)/(pressureMax-pressureZero); //conversion equation to convert analog reading to psi
   //pressureValueBAR = pressureValue * 0.0689475729;
   Serial.print(pressureValue, 2); //prints value from previous line to serial
   pressureInt = int(pressureValue);
   Serial.write(pressureInt);
   Serial.println(" psi"); //prints label to serial
   //Serial.print(pressureValueBAR, 4);
   //Serial.println(" BAR");
   delay(sensorreadDelay); //delay in milliseconds between read values
 }