from pin import Rasp, Ard
import time

# 아두이노 시리얼 포트 설정 (사용자 환경에 맞게 변경해주세요!)
ARDUINO_PORT = "/dev/ttyACM0" # 예: Windows에서는 'COM3', macOS/Linux에서는 '/dev/ttyACM0' 등

RASP_LED_PIN = 17  # 라즈베리파이 LED 핀 번호
ARD_LED_PIN = 13   # 아두이노 LED 핀 번호

# Rasp와 Ard 객체 초기화
rasp_initialized = False
arduino = None

try:
    # 1. 라즈베리파이 GPIO 초기화
    print("라즈베리파이 GPIO 초기화 중...")
    Rasp.Setup()
    rasp_initialized = True
    print("라즈베리파이 GPIO 초기화 완료.")

    # 2. 아두이노 시리얼 연결 초기화
    print(f"아두이노 시리얼 연결 중... (포트: {ARDUINO_PORT})")
    arduino = Ard(port=ARDUINO_PORT, baud=9600)
    print("아두이노 시리얼 연결 완료.")

    print(f"라즈베리파이 핀 {RASP_LED_PIN}과 아두이노 핀 {ARD_LED_PIN}의 조명을 껐다 켜는 중...")

    for i in range(5): # 5번 반복
        print(f"--- Cycle {i+1} ---")
        # 조명 켜기
        Rasp.Write(RASP_LED_PIN, 1)
        arduino.Write(ARD_LED_PIN, 1)
        print("조명 켜짐")
        time.sleep(1) # 1초 대기

        # 조명 끄기
        Rasp.Write(RASP_LED_PIN, 0)
        arduino.Write(ARD_LED_PIN, 0)
        print("조명 꺼짐")
        time.sleep(1) # 1초 대기

    print("예제 실행 완료.")

except Exception as e:
    print(f"오류 발생: {e}")

finally:
    # 3. 사용 후 정리
    print("정리 중...")
    if arduino:
        try:
            arduino.Clean()
            print("아두이노 연결 정리 완료.")
        except Exception as e:
            print(f"아두이노 정리 중 오류 발생: {e}")
    if rasp_initialized:
        try:
            Rasp.Clean()
            print("라즈베리파이 GPIO 정리 완료.")
        except Exception as e:
            print(f"라즈베리파이 정리 중 오류 발생: {e}")
    print("모든 정리 완료.")
