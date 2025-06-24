import lgpio
import pigpio
from time import sleep, time

class pin:
    handle = None         # lgpio 핸들
    pi = None             # pigpio 인스턴스

    @staticmethod
    def Setup(chip=0):
        """ GPIO 칩 열기 (lgpio) + pigpio 연결 """

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
        """ 입력 설정 후 읽기 (lgpio) """
        lgpio.gpio_claim_input(pin.handle, pin_num)
        return lgpio.gpio_read(pin.handle, pin_num)

    @staticmethod
    def Write(pin_num, value):
        """ 출력 설정 후 쓰기 (lgpio) """
        lgpio.gpio_claim_output(pin.handle, pin_num)
        lgpio.gpio_write(pin.handle, pin_num, value)

    @staticmethod
    def Free(pin_num):
        """ 핀 해제 (lgpio) """
        lgpio.gpio_free(pin.handle, pin_num)

    @staticmethod
    def Edge(pin_num, mode):
        """
        엣지(인터럽트) 감지 설정 (lgpio)
        mode: "up" | "down" | "all"
        """
        if mode == "up":
            lgpio.gpio_claim_alert(pin.handle, pin_num, lgpio.RISING_EDGE)
        elif mode == "down":
            lgpio.gpio_claim_alert(pin.handle, pin_num, lgpio.FALLING_EDGE)
        elif mode == "all":
            lgpio.gpio_claim_alert(pin.handle, pin_num, lgpio.BOTH_EDGES)
        else:
            return 0

    @staticmethod
    def GetDistance(trig_pin, echo_pin, timeout_s=0.04):
        """
        초음파 센서 거리 측정 (lgpio)
        """
        lgpio.gpio_claim_output(pin.handle, trig_pin)
        lgpio.gpio_claim_input(pin.handle, echo_pin)

        lgpio.gpio_write(pin.handle, trig_pin, 0)
        sleep(0.000002)  # 2us
        lgpio.gpio_write(pin.handle, trig_pin, 1)
        sleep(0.00001)   # 10us
        lgpio.gpio_write(pin.handle, trig_pin, 0)

        start_time = time()
        timeout_time = start_time + timeout_s

        while lgpio.gpio_read(pin.handle, echo_pin) == 0:
            start_time = time()
            if start_time > timeout_time:
                return -1

        stop_time = time()
        while lgpio.gpio_read(pin.handle, echo_pin) == 1:
            stop_time = time()
            if stop_time > timeout_time:
                return -1

        elapsed = stop_time - start_time
        distance_cm = (elapsed * 34300) / 2
        return distance_cm

    @staticmethod
    def ServoWrite(pin_num, angle):
        """
        서보모터 제어 (pigpio 사용)
        angle: 0 ~ 180 도
        """
        if pin.pi is None:
            raise Exception("pigpio 인스턴스 없음. Setup() 먼저 호출하세요.")

        if not (0 <= angle <= 180):
            raise ValueError("angle은 0~180 사이여야 합니다.")

        pulse_width = int(500 + (angle / 180) * 2000)
        pin.pi.set_servo_pulsewidth(pin_num, pulse_width)

    @staticmethod
    def ServoStop(pin_num):
        """
        서보 PWM 정지 (pigpio 사용)
        """
        if pin.pi is None:
            raise Exception("pigpio 인스턴스 없음. Setup() 먼저 호출하세요.")

        pin.pi.set_servo_pulsewidth(pin_num, 0)

    @staticmethod
    def Clean():
        """ lgpio 핸들 닫기 + pigpio 연결 해제 """
        if pin.handle is not None:
            lgpio.gpiochip_close(pin.handle)
            pin.handle = None

        if pin.pi is not None:
            pin.pi.stop()
            pin.pi = None
