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
    def __init__(self, port="/dev/ttyACM0", baud=9600):
        self.ser = None
        self.used_pins = set()
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)  # 아두이노 초기화 대기
        except serial.SerialException as e:
            raise Exception(f"시리얼 포트 연결 실패: {e}")

    def send(self, cmd):
        if self.ser is None:
            raise Exception("Arduino가 Setup 되지 않았습니다.")
        self.ser.write((cmd + "\n").encode())

    def receive(self):
        if self.ser is None:
            raise Exception("Arduino가 Setup 되지 않았습니다.")
        return self.ser.readline().decode().strip()

    def pin_mode(self, pin_num, mode):
        self.send(f"PINMODE {pin_num} {mode}")
        self.used_pins.add(pin_num)

    def write(self, pin_num, value):
        if isinstance(value, int):
            value = "HIGH" if value else "LOW"
        elif str(value).strip() == "1":
            value = "HIGH"
        elif str(value).strip() == "0":
            value = "LOW"

        self.send(f"DWRITE {pin_num} {value}")
        self.used_pins.add(pin_num)

    def read(self, pin_num):
        self.send(f"DREAD {pin_num}")
        val = self.receive()
        self.used_pins.add(pin_num)
        return val

    def analog_write(self, pin_num, value):
        self.send(f"AWRITE {pin_num} {value}")
        self.used_pins.add(pin_num)

    def analog_read(self, pin_num):
        self.send(f"AREAD {pin_num}")
        val = self.receive()
        self.used_pins.add(pin_num)
        return val

    def servo_write(self, pin_num, angle):
        if not (0 <= angle <= 180):
            raise ValueError("angle은 0~180 사이여야 합니다.")
        self.send(f"SERVOWRITE {pin_num} {angle}")
        self.used_pins.add(pin_num)

    def servo_stop(self, pin_num):
        self.send(f"SERVOSTOP {pin_num}")
        self.used_pins.add(pin_num)

    def close(self):
        if self.ser is not None:
            self.ser.close()
            self.ser = None
            self.used_pins.clear()
