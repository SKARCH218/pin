# pin.py - Raspberry Pi GPIO 제어 유틸리티

## 소개

이 라이브러리는 Raspberry Pi에서 `lgpio`와 `pigpio`를 결합하여
하나의 `pin` 클래스로 GPIO, 초음파 센서, 서보 모터를 간편하게 제어할 수 있도록 설계되었습니다.

- `lgpio` : 일반 GPIO 입출력, 인터럽트, 초음파 거리 측정용
- `pigpio` : 정밀한 PWM 신호를 요구하는 서보모터 제어용

---

## ⚙️ 주요 기능

| 메서드 | 설명 |
|--------|------|
| `Setup()` | `lgpio` 핸들 열기 + `pigpio` 연결 |
| `Read(pin_num)` | 디지털 입력 읽기 |
| `Write(pin_num, value)` | 디지털 출력 쓰기 |
| `Edge(pin_num, mode)` | 상승/하강/양쪽 엣지 인터럽트 설정 |
| `GetDistance(trig_pin, echo_pin)` | 초음파 센서 거리 측정 |
| `ServoWrite(pin_num, angle)` | 서보 모터 각도 설정 |
| `ServoStop(pin_num)` | 서보 모터 PWM 정지 |
| `Clean()` | `lgpio` 핸들 닫기 + `pigpio` 연결 종료 |

---

## 의존성

- Python 3.x
- [lgpio](https://abyz.me.uk/lg/py_lgpio.html)
- [pigpio](http://abyz.me.uk/rpi/pigpio/python.html)

---

## 설치

```bash
# pigpio 설치 (이미 설치된 경우 생략)
sudo apt-get install pigpio python3-pigpio
```

# lgpio 설치 (예시)
pip install lgpio

# 사용 예시
```python
from pin import pin
from time import sleep

# GPIO, pigpio 초기화
pin.Setup()

# 서보 모터 (GPIO 24)에 90도 출력
pin.ServoWrite(24, 90)
sleep(2)
pin.ServoWrite(24, 0)

# 초음파 센서 거리 측정
distance = pin.GetDistance(18, 23)
print(f"거리: {distance:.2f} cm")

# 정리
pin.ServoStop(24)
pin.Clean()
```

# 주의사항
## 서보모터를 사용할 때는 반드시 pigpiod 데몬을 실행해야 합니다.
```bash
sudo pigpiod
```
## 혹은 Python에서 자동 실행하고 싶다면:
```python
import os
os.system("sudo pigpiod")
Clean() 메서드를 호출하여 사용이 끝난 후 자원을 반납하세요.
```

# 라이선스
자유롭게 수정 및 사용 가능. 필요하다면 라이선스 파일 추가하세요!
SKARCH218 제작
