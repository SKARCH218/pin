# `pin.py` 라이브러리 사용 가이드

`pin.py`는 라즈베리파이의 GPIO와 아두이노를 파이썬으로 쉽게 제어하기 위한 라이브러리입니다. 이 가이드는 `Rasp` 클래스와 `Ard` 클래스의 주요 기능과 사용법을 설명합니다.

## 사전 준비

### 1. 라이브러리 설치
먼저, 필요한 파이썬 라이브러리를 설치해야 합니다.

```bash
pip install lgpio pyserial
```

### 2. 아두이노 스케치 업로드
`Ard` 클래스를 사용하려면, 함께 제공되는 아두이노 스케치를 대상 아두이노 보드에 업로드해야 합니다. 이 스케치는 파이썬으로부터 시리얼 명령을 받아 처리하는 역할을 합니다.

- **스케치 파일:** `Ard_ino/ard.ino`

---

## `Rasp` 클래스 (라즈베리파이 GPIO 제어)

`Rasp` 클래스는 라즈베리파이의 GPIO 핀을 직접 제어하기 위한 **정적(static)** 메소드들을 제공합니다. 모든 함수는 `Rasp.FunctionName()` 형태로 호출합니다.

### 1. 초기화 및 리소스 정리 (`Setup` & `Clean`)

GPIO 사용을 시작하기 전 반드시 `Setup()`을 호출하고, 프로그램이 종료될 때 `Clean()`을 호출하여 사용한 모든 리소스를 안전하게 해제해야 합니다. `try...finally` 구문을 사용하는 것이 좋습니다.

```python
from rpi_arduino_pin.pin import Rasp
import time

# GPIO 핸들 초기화 (프로그램 시작 시 1회)
Rasp.Setup()

try:
    # 여기에 GPIO 제어 코드를 작성합니다.
    print("GPIO 17번 핀에 1초간 HIGH 신호를 출력합니다.")
    Rasp.Write(17, 1)
    time.sleep(1)
    Rasp.Write(17, 0)

finally:
    # 프로그램 종료 시 모든 GPIO 리소스를 정리합니다.
    Rasp.Clean()
    print("GPIO가 정리되었습니다.")
```

### 2. 디지털 입출력 (Digital I/O)

- `Rasp.Write(pin_num, value)`: 지정된 핀에 디지털 신호(1: HIGH, 0: LOW)를 출력합니다.
- `Rasp.Read(pin_num)`: 지정된 핀의 디지털 상태를 읽어 1 또는 0을 반환합니다.

```python
# GPIO 17번 핀에 출력
Rasp.Write(17, 1)

# GPIO 27번 핀에서 입력
pin_status = Rasp.Read(27)
print(f"GPIO 27번 핀의 상태: {pin_status}")
```

### 3. 서보 모터 제어 (Servo Control)

- `Rasp.ServoWrite(pin_num, angle)`: 지정된 핀에 연결된 서보 모터를 `angle` (0~180도)로 회전시킵니다.
- `Rasp.ServoStop(pin_num)`: 해당 핀의 PWM 출력을 중지하여 서보 모터 작동을 멈춥니다.

```python
# GPIO 18번 핀의 서보 모터를 90도로 이동
Rasp.ServoWrite(18, 90)
time.sleep(1)

# 서보 모터 정지
Rasp.ServoStop(18)
```

### 4. 초음파 센서 거리 측정 (HC-SR04)

- `Rasp.GetDistance(trig_pin, echo_pin)`: Trig/Echo 핀을 사용하여 거리를 cm 단위로 측정합니다. 측정 실패 시 -1을 반환합니다.

```python
# Trig: GPIO 23, Echo: GPIO 24
distance = Rasp.GetDistance(23, 24)
if distance != -1:
    print(f"측정된 거리: {distance:.2f} cm")
else:
    print("거리 측정 실패")
```

---

## `Ard` 클래스 (아두이노 시리얼 제어)

`Ard` 클래스는 시리얼 통신을 통해 아두이노를 제어합니다. **인스턴스 기반**으로 작동하므로, 여러 개의 아두이노를 각기 다른 포트로 연결하여 동시에 제어할 수 있습니다.

### 1. 아두이노 연결 및 종료

`Ard` 객체를 생성하여 아두이노와 연결하고, 사용이 끝나면 `Clean()` 메소드를 호출하여 연결을 종료하고 아두이노의 서보 등을 초기화합니다.

```python
from rpi_arduino_pin.pin import Ard
import time

# Ard 객체 생성 (포트와 통신 속도 지정)
# 여러 아두이노가 있다면 객체를 여러 개 생성하면 됩니다.
uno = Ard(port="/dev/ttyACM0", baud=9600)
# mega = Ard(port="/dev/ttyACM1", baud=9600)

try:
    # 아두이노 13번 핀의 LED를 1초간 켭니다.
    uno.Write(13, 1)
    time.sleep(1)
    uno.Write(13, 0)

finally:
    # 시리얼 연결을 닫고 아두이노 리소스를 정리합니다.
    uno.Clean()
    print("아두이노 연결이 종료되었습니다.")
```

### 2. 핀 제어 (Digital & Analog)

`Ard` 클래스의 입출력 메소드는 호출 시 자동으로 아두이노의 핀 모드를 설정하므로 편리합니다.

- `Ard.Write(pin_num, value)`: 디지털 핀에 `value`(0 또는 1)를 씁니다.
- `Ard.Read(pin_num)`: 디지털 핀의 값을 읽습니다.
- `Ard.AnalogWrite(pin_num, value)`: PWM 핀에 `value`(0~255)를 씁니다.
- `Ard.AnalogRead(pin_num)`: 아날로그 핀의 값을 읽습니다. (A0, A1, ... 핀은 0, 1, ... 로 지정)

```python
# 디지털 출력
uno.Write(8, 1) # 8번 핀 HIGH

# 아날로그 입력 (A0 핀)
sensor_value = uno.AnalogRead(0)
print(f"아날로그 A0 핀 센서 값: {sensor_value}")

# PWM 출력 (아두이노 9번 핀)
uno.AnalogWrite(9, 128) # 50% 밝기
```

### 3. 서보 모터 제어

- `Ard.ServoWrite(pin_num, angle)`: 아두이노의 지정된 핀에 연결된 서보를 `angle`(0~180도)로 회전시킵니다.
- `Ard.ServoStop(pin_num)`: 서보 작동을 중지하고 핀에서 분리(detach)합니다.

```python
# 아두이노 9번 핀의 서보를 45도로 이동
uno.ServoWrite(9, 45)
time.sleep(1)

# 서보 정지
uno.ServoStop(9)
```

### 4. 인터럽트 감지 (Interrupt Handling)

아두이노의 외부 인터럽트 기능을 파이썬에서 비동기적으로 사용할 수 있습니다. 인터럽트가 발생하면 등록된 파이썬 콜백 함수가 실행됩니다. (참고: Arduino Uno는 2, 3번 핀에서만 인터럽트를 지원합니다.)

- `Ard.Edge(pin_num, mode, callback)`: 인터럽트를 설정합니다.
  - `mode`: `"RISING"`, `"FALLING"`, `"BOTH"` 중 하나를 지정합니다.
  - `callback`: 인터럽트 발생 시 호출될 파이썬 함수. 이 함수는 `pin_num`과 `value` 두 개의 인자를 받습니다.
- `Ard.DetachEdge(pin_num)`: 설정된 인터럽트를 해제합니다.

```python
from rpi_arduino_pin.pin import Ard
import time
import sys

# 인터럽트가 발생했을 때 실행될 콜백 함수
def my_callback(pin, value):
    print(f"인터럽트 발생! | 핀 번호: {pin} | 디지털 값: {value}")
    # 이 곳에서 원하는 작업을 수행할 수 있습니다.

uno = Ard(port="/dev/ttyACM0", baud=9600)

try:
    # 아두이노 2번 핀에 RISING 엣지 감지 인터럽트 설정
    uno.Edge(2, "RISING", my_callback)
    print("아두이노 2번 핀에 인터럽트가 설정되었습니다.")
    print("버튼을 누르거나, 핀에 RISING 신호를 인가해보세요.")
    print("프로그램을 종료하려면 Ctrl+C를 누르세요.")

    # 콜백이 호출되는 동안 메인 스레드가 대기하도록 설정
    while True:
        time.sleep(0.1)

except KeyboardInterrupt:
    print("
프로그램 종료 중...")

finally:
    # 리소스 정리
    uno.Clean()
    print("아두이노 연결이 종료되었습니다.")
```