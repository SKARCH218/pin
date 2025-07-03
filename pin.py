import lgpio
import pigpio
import serial
import time

class Rasp:
    handle = None
    pi = None
    used_pins = set()  # 사용한 핀 기록

    @staticmethod
    def Setup(chip=0):
        if Rasp.handle is None:
            Rasp.handle = lgpio.gpiochip_open(chip)
        else:
            raise Exception("이미 GPIO handle이 열려있습니다.")

        if Rasp.pi is None:
            Rasp.pi = pigpio.pi()
            if not Rasp.pi.connected:
                raise Exception("pigpio 데몬 연결 실패! 'sudo pigpiod' 실행 필요")

    @staticmethod
    def Read(pin_num):
        lgpio.gpio_claim_input(Rasp.handle, pin_num)
        Rasp.used_pins.add(pin_num)
        return lgpio.gpio_read(Rasp.handle, pin_num)

    @staticmethod
    def Write(pin_num, value):
        lgpio.gpio_claim_output(Rasp.handle, pin_num)
        lgpio.gpio_write(Rasp.handle, pin_num, value)
        Rasp.used_pins.add(pin_num)

    @staticmethod
    def Free(pin_num):
        lgpio.gpio_free(Rasp.handle, pin_num)
        Rasp.used_pins.discard(pin_num)

    @staticmethod
    def Edge(pin_num, mode):
        if mode == "up":
            lgpio.gpio_claim_alert(Rasp.handle, pin_num, lgpio.RISING_EDGE)
        elif mode == "down":
            lgpio.gpio_claim_alert(Rasp.handle, pin_num, lgpio.FALLING_EDGE)
        elif mode == "all":
            lgpio.gpio_claim_alert(Rasp.handle, pin_num, lgpio.BOTH_EDGES)
        else:
            return 0
        Rasp.used_pins.add(pin_num)

    @staticmethod
    def GetDistance(trig_pin, echo_pin, timeout_s=0.1):  # timeout 0.1초로 늘림
        lgpio.gpio_claim_output(Rasp.handle, trig_pin)
        lgpio.gpio_claim_input(Rasp.handle, echo_pin)
        Rasp.used_pins.update([trig_pin, echo_pin])

        lgpio.gpio_write(Rasp.handle, trig_pin, 0)
        time.sleep(0.000002)
        lgpio.gpio_write(Rasp.handle, trig_pin, 1)
        time.sleep(0.00001)  # 10us 트리거 신호
        lgpio.gpio_write(Rasp.handle, trig_pin, 0)

        start_time = time()
        timeout_time = start_time + timeout_s

        while lgpio.gpio_read(Rasp.handle, echo_pin) == 0:
            current_time = time()
            if current_time > timeout_time:
                return -1

        pulse_start = time()
        while lgpio.gpio_read(Rasp.handle, echo_pin) == 1:
            current_time = time()
            if current_time > timeout_time:
                return -1

        pulse_end = time()
        elapsed = pulse_end - pulse_start

        distance_cm = (elapsed * 34300) / 2
        return distance_cm

    @staticmethod
    def ServoWrite(pin_num, angle):
        if Rasp.pi is None:
            raise Exception("pigpio 인스턴스 없음. Setup() 먼저 호출하세요.")

        if not (0 <= angle <= 180):
            raise ValueError("angle은 0~180 사이여야 합니다.")

        pulse_width = int(500 + (angle / 180) * 2000)
        Rasp.pi.set_servo_pulsewidth(pin_num, pulse_width)

    @staticmethod
    def ServoStop(pin_num):
        if Rasp.pi is None:
            raise Exception("pigpio 인스턴스 없음. Setup() 먼저 호출하세요.")

        Rasp.pi.set_servo_pulsewidth(pin_num, 0)

    @staticmethod
    def Clean(all=False):
        """ 핸들 닫기 + 사용 핀 해제 + pigpio 정리
            all=True일 경우 0~27 모든 핀을 0으로 출력 후 해제
            all=False일 경우 사용된 핀만 0으로 출력 후 해제
        """
        if Rasp.handle is not None:
            if all:
                for pin_num in range(0, 28):  # GPIO 0 ~ 27
                    try:
                        lgpio.gpio_claim_output(Rasp.handle, pin_num)
                        lgpio.gpio_write(Rasp.handle, pin_num, 0)
                        lgpio.gpio_free(Rasp.handle, pin_num)
                    except Exception:
                        pass  # 사용 불가능한 핀 무시
            else:
                for pin_num in list(Rasp.used_pins):
                    try:
                        lgpio.gpio_claim_output(Rasp.handle, pin_num)
                        lgpio.gpio_write(Rasp.handle, pin_num, 0)
                        lgpio.gpio_free(Rasp.handle, pin_num)
                    except Exception:
                        pass
                Rasp.used_pins.clear()

            lgpio.gpiochip_close(Rasp.handle)
            Rasp.handle = None

        if Rasp.pi is not None:
            Rasp.pi.stop()
            Rasp.pi = None

class Ard:
    ser = None
    used_pins = set()

    @staticmethod
    def Setup(port="/dev/ttyACM0", baud=9600):
        if Ard.ser is None:
            Ard.ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)  # 아두이노 초기화 대기
        else:
            raise Exception("이미 시리얼 연결이 열려있습니다.")

    @staticmethod
    def send(cmd):
        if Ard.ser is None:
            raise Exception("Arduino가 Setup 되지 않았습니다.")
        Ard.ser.write((cmd + "\n").encode())

    @staticmethod
    def receive():
        if Ard.ser is None:
            raise Exception("Arduino가 Setup 되지 않았습니다.")
        return Ard.ser.readline().decode().strip()

    @staticmethod
    def pin_mode(pin_num, mode):
        Ard.send(f"PINMODE {pin_num} {mode}")
        Ard.used_pins.add(pin_num)

    @staticmethod
    def digital_write(pin_num, value):
        if isinstance(value, int):
            value = "HIGH" if value else "LOW"
        elif str(value).strip() == "1":
            value = "HIGH"
        elif str(value).strip() == "0":
            value = "LOW"

        Ard.send(f"DWRITE {pin_num} {value}")
        Ard.used_pins.add(pin_num)

    @staticmethod
    def digital_read(pin_num):
        Ard.send(f"DREAD {pin_num}")
        val = Ard.receive()
        Ard.used_pins.add(pin_num)
        return val

    @staticmethod
    def analog_write(pin_num, value):
        Ard.send(f"AWRITE {pin_num} {value}")
        Ard.used_pins.add(pin_num)

    @staticmethod
    def analog_read(pin_num):
        Ard.send(f"AREAD {pin_num}")
        val = Ard.receive()
        Ard.used_pins.add(pin_num)
        return val

    @staticmethod
    def servo_write(pin_num, angle):
        if not (0 <= angle <= 180):
            raise ValueError("angle은 0~180 사이여야 합니다.")
        Ard.send(f"SERVOWRITE {pin_num} {angle}")
        Ard.used_pins.add(pin_num)

    @staticmethod
    def servo_stop(pin_num):
        Ard.send(f"SERVOSTOP {pin_num}")
        Ard.used_pins.add(pin_num)

    @staticmethod
    def Close():
        if Ard.ser is not None:
            Ard.ser.close()
            Ard.ser = None
            Ard.used_pins.clear()
