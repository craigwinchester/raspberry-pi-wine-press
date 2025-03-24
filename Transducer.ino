/*
  Pressure Transducer Reading
  
  This sketch reads an analog signal from a pressure transducer 
  and converts it to PSI based on the calibration values:
  - 0.5V = 0 PSI
  - 4.5V = 30 PSI
  
  The PSI value is printed to the Serial Monitor.
*/

// Constants
const int sensorPin = A0;      // Analog pin where pressure transducer is connected
const float voltageMin = 0.5;  // Voltage at 0 PSI (0.5V)
const float voltageMax = 4.5;  // Voltage at max PSI (4.5V)
const float psiMin = 0.0;      // Minimum PSI reading (0 PSI)
const float psiMax = 30.0;     // Maximum PSI reading (30 PSI)

// Variables
float sensorValue = 0;  // Value read from the sensor
float voltage = 0;      // Voltage calculated from sensor reading
float psi = 0;  // Calculated PSI value
float bar = 0; 

void setup() {
  // Initialize serial communication at 9600 bps
  Serial.begin(9600);
  //  Serial.println("Pressure Transducer Reading");
  //  Serial.println("---------------------------");
  //  Serial.println("Calibration: 0.5V = 0 PSI, 4.5V = 30 PSI");
  //  Serial.println();
}

void loop() {
  // Read the analog value from sensor
  sensorValue = analogRead(sensorPin);
  
  // Convert analog reading (0-1023) to voltage (0-5V)
  voltage = sensorValue * (5.0 / 1023.0);
  
  // Convert voltage to PSI using linear mapping
  if (voltage <= voltageMin) {
    psi = psiMin;
  } else if (voltage >= voltageMax) {
    psi = psiMax;
  } else {
    // Map voltage to PSI using the voltage and PSI ranges
    psi = psiMin + (psiMax - psiMin) * ((voltage - voltageMin) / (voltageMax - voltageMin));
    bar = psi * 0.0689476;
  }
  
  // Print the results
  // Serial.print("Sensor Reading: ");
  // Serial.print(sensorValue);
  // Serial.print("\tVoltage: ");
  // Serial.print(voltage, 2);  // 2 decimal places
  // Serial.print("V\tPressure: ");
  // Serial.print(psi, 2);  // 2 decimal places
  // Serial.println(" PSI");
  Serial.println(bar, 2);
  // Serial.println(" Bar");
  
  // Wait a bit before taking the next reading
  delay(250);
}
