#include <Servo.h>

#define MAX_SERVOS 8 // 최대 8개의 서보 모터 제어 지원

Servo servos[MAX_SERVOS];
int servo_pins[MAX_SERVOS]; // 각 서보 객체에 연결된 핀 번호 저장
bool servo_attached_status[MAX_SERVOS]; // 각 서보 객체의 연결 상태 추적
int attached_servo_count = 0; // 현재 연결된 서보 모터 수

// 인터럽트 관련 변수 및 함수
// Arduino Uno: Interrupt 0 -> Digital Pin 2, Interrupt 1 -> Digital Pin 3
// 다른 보드는 핀-인터럽트 매핑이 다를 수 있습니다.

volatile int interruptPinState[2]; // 0: Pin 2, 1: Pin 3

void handleInterrupt0() {
  interruptPinState[0] = digitalRead(2);
  Serial.print("INTERRUPT 2 ");
  Serial.println(interruptPinState[0]);
}

void handleInterrupt1() {
  interruptPinState[1] = digitalRead(3);
  Serial.print("INTERRUPT 3 ");
  Serial.println(interruptPinState[1]);
}

// 주어진 핀에 연결된 서보의 인덱스를 찾습니다.
int findServoIndex(int pin) {
  for (int i = 0; i < MAX_SERVOS; i++) {
    if (servo_attached_status[i] && servo_pins[i] == pin) {
      return i;
    }
  }
  return -1; // 찾지 못함
}

// 사용 가능한 서보 슬롯의 인덱스를 찾습니다.
int findAvailableServoSlot() {
  for (int i = 0; i < MAX_SERVOS; i++) {
    if (!servo_attached_status[i]) {
      return i;
    }
  }
  return -1; // 사용 가능한 슬롯 없음
}

void setup() {
  Serial.begin(9600);
  while (!Serial); // 시리얼 초기화 대기

  // 서보 추적 배열 초기화
  for (int i = 0; i < MAX_SERVOS; i++) {
    servo_attached_status[i] = false;
    servo_pins[i] = -1;
  }
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim(); // 공백 제거

    if (cmd.startsWith("PINMODE")) {
      int pin = cmd.substring(8, cmd.indexOf(' ', 8)).toInt();
      String mode = cmd.substring(cmd.indexOf(' ', 8) + 1);
      if (mode == "OUTPUT") {
        pinMode(pin, OUTPUT);
      } else if (mode == "INPUT") {
        pinMode(pin, INPUT);
      }
    }

    else if (cmd.startsWith("DWRITE")) {
      int pin = cmd.substring(7, cmd.indexOf(' ', 7)).toInt();
      String val = cmd.substring(cmd.indexOf(' ', 7) + 1);
      digitalWrite(pin, val == "HIGH" ? HIGH : LOW);
    }

    else if (cmd.startsWith("DREAD")) {
      int pin = cmd.substring(6).toInt();
      int val = digitalRead(pin);
      Serial.println(val);
    }

    else if (cmd.startsWith("AWRITE")) {
      int pin = cmd.substring(7, cmd.indexOf(' ', 7)).toInt();
      int val = cmd.substring(cmd.indexOf(' ', 7) + 1).toInt();
      analogWrite(pin, val);
    }

    else if (cmd.startsWith("AREAD")) {
      int pin = cmd.substring(6).toInt();
      int val = analogRead(pin);
      Serial.println(val);
    }

    else if (cmd.startsWith("SERVOWRITE")) {
      int pin = cmd.substring(10, cmd.indexOf(' ', 10)).toInt();
      int angle = cmd.substring(cmd.indexOf(' ', 10) + 1).toInt();

      int servoIdx = findServoIndex(pin);
      if (servoIdx == -1) { // 해당 핀에 서보가 아직 연결되지 않음
        servoIdx = findAvailableServoSlot();
        if (servoIdx != -1) { // 사용 가능한 슬롯이 있음
          servos[servoIdx].attach(pin);
          servo_pins[servoIdx] = pin;
          servo_attached_status[servoIdx] = true;
          attached_servo_count++;
        } else {
          Serial.println("ERROR: Max servos attached"); // 최대 서보 수 초과
          return;
        }
      }
      servos[servoIdx].write(angle);
    }

    else if (cmd.startsWith("SERVOSTOP")) {
      int pin = cmd.substring(10).toInt();
      int servoIdx = findServoIndex(pin);
      if (servoIdx != -1) { // 해당 핀에 서보가 연결되어 있음
        servos[servoIdx].detach();
        servo_attached_status[servoIdx] = false;
        servo_pins[servoIdx] = -1; // 핀 정보 초기화
        attached_servo_count--;
      } else {
        Serial.println("ERROR: Servo not attached to this pin"); // 해당 핀에 서보가 연결되지 않음
      }
    }
    // 모든 서보를 해제하는 명령 추가
    else if (cmd.startsWith("CLEANALLSERVOS")) {
      for (int i = 0; i < MAX_SERVOS; i++) {
        if (servo_attached_status[i]) {
          servos[i].detach();
          servo_attached_status[i] = false;
          servo_pins[i] = -1;
        }
      }
      attached_servo_count = 0;
      Serial.println("OK: All servos detached"); // 성공 응답
    }
    
    // 인터럽트 관련 명령 추가
    else if (cmd.startsWith("ATTACH_INTERRUPT")) {
      int pin = cmd.substring(17, cmd.indexOf(' ', 17)).toInt();
      String modeStr = cmd.substring(cmd.indexOf(' ', 17) + 1);
      int mode;

      if (modeStr == "RISING") mode = RISING;
      else if (modeStr == "FALLING") mode = FALLING;
      else if (modeStr == "BOTH") mode = CHANGE;
      else {
        Serial.println("ERROR: Invalid interrupt mode");
        return;
      }

      if (pin == 2) {
        attachInterrupt(digitalPinToInterrupt(2), handleInterrupt0, mode);
        Serial.println("OK: Interrupt attached to pin 2");
      } else if (pin == 3) {
        attachInterrupt(digitalPinToInterrupt(3), handleInterrupt1, mode);
        Serial.println("OK: Interrupt attached to pin 3");
      } else {
        Serial.println("ERROR: Pin does not support interrupts");
      }
    }
    else if (cmd.startsWith("DETACH_INTERRUPT")) {
      int pin = cmd.substring(17).toInt();
      if (pin == 2) {
        detachInterrupt(digitalPinToInterrupt(2));
        Serial.println("OK: Interrupt detached from pin 2");
      } else if (pin == 3) {
        detachInterrupt(digitalPinToInterrupt(3));
        Serial.println("OK: Interrupt detached from pin 3");
      } else {
        Serial.println("ERROR: Pin does not support interrupts");
      }
    }
    else {
      Serial.println("ERROR: Unknown command"); // 알 수 없는 명령에 대한 에러 응답
    }
  }
}