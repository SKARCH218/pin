import lgpio
import pigpio
from time import sleep, time

class pin:
    handle = None
    pi = None
    used_pins = set()  # 사용한 핀 기록

    @staticmethod
    def Setup(chip=0):
        if pin.handle is None:
            pin.handle = lgpio.gpiochip_open(chip)
        else:
            raise Exception("이미 GPIO handle이 열려있습니다.")

        if pin.pi is None:
            pin.pi = pigpio.pi()
            if not pin.pi.connected:
                raise Exception("pigpio 데몬 연결 실패! 'sudo pigpiod' 실행 필요")

    @staticmethod
    def Read(pin_num):
        lgpio.gpio_claim_input(pin.handle, pin_num)
        pin.used_pins.add(pin_num)
        return lgpio.gpio_read(pin.handle, pin_num)

    @staticmethod
    def Write(pin_num, value):
        lgpio.gpio_claim_output(pin.handle, pin_num)
        lgpio.gpio_write(pin.handle, pin_num, value)
        pin.used_pins.add(pin_num)

    @staticmethod
    def Free(pin_num):
        lgpio.gpio_free(pin.handle, pin_num)
        pin.used_pins.discard(pin_num)

    @staticmethod
    def Edge(pin_num, mode):
        if mode == "up":
            lgpio.gpio_claim_alert(pin.handle, pin_num, lgpio.RISING_EDGE)
        elif mode == "down":
            lgpio.gpio_claim_alert(pin.handle, pin_num, lgpio.FALLING_EDGE)
        elif mode == "all":
            lgpio.gpio_claim_alert(pin.handle, pin_num, lgpio.BOTH_EDGES)
        else:
            return 0
        pin.used_pins.add(pin_num)

    @staticmethod
    def GetDistance(trig_pin, echo_pin, timeout_s=0.1):  # timeout 0.1초로 늘림
        lgpio.gpio_claim_output(pin.handle, trig_pin)
        lgpio.gpio_claim_input(pin.handle, echo_pin)
        pin.used_pins.update([trig_pin, echo_pin])

        lgpio.gpio_write(pin.handle, trig_pin, 0)
        sleep(0.000002)
        lgpio.gpio_write(pin.handle, trig_pin, 1)
        sleep(0.00001)  # 10us 트리거 신호
        lgpio.gpio_write(pin.handle, trig_pin, 0)

        start_time = time()
        timeout_time = start_time + timeout_s

        while lgpio.gpio_read(pin.handle, echo_pin) == 0:
            current_time = time()
            if current_time > timeout_time:
                return -1

        pulse_start = time()
        while lgpio.gpio_read(pin.handle, echo_pin) == 1:
            current_time = time()
            if current_time > timeout_time:
                return -1

        pulse_end = time()
        elapsed = pulse_end - pulse_start

        distance_cm = (elapsed * 34300) / 2
        return distance_cm

    @staticmethod
    def ServoWrite(pin_num, angle):
        if pin.pi is None:
            raise Exception("pigpio 인스턴스 없음. Setup() 먼저 호출하세요.")

        if not (0 <= angle <= 180):
            raise ValueError("angle은 0~180 사이여야 합니다.")

        pulse_width = int(500 + (angle / 180) * 2000)
        pin.pi.set_servo_pulsewidth(pin_num, pulse_width)

    @staticmethod
    def ServoStop(pin_num):
        if pin.pi is None:
            raise Exception("pigpio 인스턴스 없음. Setup() 먼저 호출하세요.")

        pin.pi.set_servo_pulsewidth(pin_num, 0)

    @staticmethod
    def Clean(all=False):
        """ 핸들 닫기 + 사용 핀 해제 + pigpio 정리
            all=True일 경우 0~27 모든 핀을 0으로 출력 후 해제
            all=False일 경우 사용된 핀만 0으로 출력 후 해제
        """
        if pin.handle is not None:
            if all:
                for pin_num in range(0, 28):  # GPIO 0 ~ 27
                    try:
                        lgpio.gpio_claim_output(pin.handle, pin_num)
                        lgpio.gpio_write(pin.handle, pin_num, 0)
                        lgpio.gpio_free(pin.handle, pin_num)
                    except Exception:
                        pass  # 사용 불가능한 핀 무시
            else:
                for pin_num in list(pin.used_pins):
                    try:
                        lgpio.gpio_claim_output(pin.handle, pin_num)
                        lgpio.gpio_write(pin.handle, pin_num, 0)
                        lgpio.gpio_free(pin.handle, pin_num)
                    except Exception:
                        pass
                pin.used_pins.clear()

            lgpio.gpiochip_close(pin.handle)
            pin.handle = None

        if pin.pi is not None:
            pin.pi.stop()
            pin.pi = None
