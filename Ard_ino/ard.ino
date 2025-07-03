#include <Servo.h>

#define MAX_SERVOS 8

Servo servos[MAX_SERVOS];
int servo_pins[MAX_SERVOS];
bool servo_attached_status[MAX_SERVOS];

int findServoIndex(int pin) {
  for (int i = 0; i < MAX_SERVOS; i++) {
    if (servo_attached_status[i] && servo_pins[i] == pin) return i;
  }
  return -1;
}

int findAvailableServoSlot() {
  for (int i = 0; i < MAX_SERVOS; i++) {
    if (!servo_attached_status[i]) return i;
  }
  return -1;
}

void detachServo(int pin) {
  int servoIdx = findServoIndex(pin);
  if (servoIdx != -1) {
    servos[servoIdx].detach();
    servo_attached_status[servoIdx] = false;
    servo_pins[servoIdx] = -1;
  }
}

void setup() {
  Serial.begin(9600);
  while (!Serial);
  for (int i = 0; i < MAX_SERVOS; i++) {
    servo_attached_status[i] = false;
    servo_pins[i] = -1;
  }
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.startsWith("PINMODE")) {
      int pin = cmd.substring(8, cmd.indexOf(' ', 8)).toInt();
      String mode = cmd.substring(cmd.indexOf(' ', 8) + 1);
      if (mode == "OUTPUT") pinMode(pin, OUTPUT);
      else if (mode == "INPUT") pinMode(pin, INPUT);
    } 
    else if (cmd.startsWith("DWRITE")) {
      int pin = cmd.substring(7, cmd.indexOf(' ', 7)).toInt();
      String val = cmd.substring(cmd.indexOf(' ', 7) + 1);
      digitalWrite(pin, val == "HIGH" ? HIGH : LOW);
    } 
    else if (cmd.startsWith("DREAD")) {
      int pin = cmd.substring(6).toInt();
      Serial.println(digitalRead(pin));
    } 
    else if (cmd.startsWith("AWRITE")) {
      int pin = cmd.substring(7, cmd.indexOf(' ', 7)).toInt();
      int val = cmd.substring(cmd.indexOf(' ', 7) + 1).toInt();
      analogWrite(pin, val);
    } 
    else if (cmd.startsWith("AREAD")) {
      int pin = cmd.substring(6).toInt();
      Serial.println(analogRead(pin));
    } 
    else if (cmd.startsWith("SERVOWRITE")) {
      int pin = cmd.substring(10, cmd.indexOf(' ', 10)).toInt();
      int angle = cmd.substring(cmd.indexOf(' ', 10) + 1).toInt();
      int servoIdx = findServoIndex(pin);
      if (servoIdx == -1) {
        servoIdx = findAvailableServoSlot();
        if (servoIdx != -1) {
          servos[servoIdx].attach(pin);
          servo_pins[servoIdx] = pin;
          servo_attached_status[servoIdx] = true;
        } else {
          Serial.println("ERROR: Max servos attached");
          return;
        }
      }
      servos[servoIdx].write(angle);
    } 
    else if (cmd.startsWith("SERVOSTOP")) {
      int pin = cmd.substring(10).toInt();
      detachServo(pin);
    }
  }
}