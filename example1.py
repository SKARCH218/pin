from pin import Rasp, Ard
from time import sleep

# 아두이노 시리얼 포트 설정 (사용자 환경에 맞게 변경해주세요!)
ARDUINO_PORT = "/dev/ttyACM0" # 예: Windows에서는 'COM3', macOS/Linux에서는 '/dev/ttyACM0' 등
arduino = None # 전역 변수 선언

RASP_LED_PIN = 17  # 라즈베리파이 LED 핀 번호
ARD_LED_PIN = 13   # 아두이노 LED 핀 번호

def setup():
    global arduino
    print("라즈베리파이 GPIO 초기화 중...")
    Rasp.Setup()
    print("라즈베리파이 GPIO 초기화 완료.")

    print(f"아두이노 시리얼 연결 중... (포트: {ARDUINO_PORT})")
    arduino = Ard(port=ARDUINO_PORT, baud=9600)
    print("아두이노 시리얼 연결 완료.")

def loop():
    print(f"라즈베리파이 핀 {RASP_LED_PIN}과 아두이노 핀 {ARD_LED_PIN}의 조명을 껐다 켜는 중...")
    for i in range(5): # 5번 반복
        print(f"--- Cycle {i+1} ---")
        # 조명 켜기
        Rasp.Write(RASP_LED_PIN, 1)
        arduino.Write(ARD_LED_PIN, 1)
        print("조명 켜짐")
        sleep(1) # 1초 대기

        # 조명 끄기
        Rasp.Write(RASP_LED_PIN, 0)
        arduino.Write(ARD_LED_PIN, 0)
        print("조명 꺼짐")
        sleep(1) # 1초 대기

def main():
    setup()
    loop()
    print("예제 실행 완료.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        print("정리 중...")
        if arduino:
            try:
                arduino.Clean()
                print("아두이노 연결 정리 완료.")
            except Exception as e:
                print(f"아두이노 정리 중 오류 발생: {e}")
        try:
            Rasp.Clean()
            print("라즈베리파이 GPIO 정리 완료.")
        except Exception as e:
            print(f"라즈베리파이 정리 중 오류 발생: {e}")
        print("모든 정리 완료.")