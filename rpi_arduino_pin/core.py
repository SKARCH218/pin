import lgpio
import serial
import time
import spidev

try:
    from gpiozero import Servo, Device
    from gpiozero.pins.lgpio import LGPIOFactory
    GPIOZERO_AVAILABLE = True
except ImportError:
    GPIOZERO_AVAILABLE = False

class Rasp:
    handle = None
    used_pins = set()
    servos = {}  # gpiozero 서보 객체 관리
    rfid_reader = None # RFID 리더 객체

    @staticmethod
    def Setup(chip=0):
        if Rasp.handle is None:
            Rasp.handle = lgpio.gpiochip_open(chip)
        else:
            raise Exception("이미 GPIO handle이 열려있습니다.")
        
        if GPIOZERO_AVAILABLE:
            # gpiozero가 lgpio를 사용하도록 설정
            Device.pin_factory = LGPIOFactory()

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
    def GetDistance(trig_pin, echo_pin, timeout_s=0.1):
        lgpio.gpio_claim_output(Rasp.handle, trig_pin)
        lgpio.gpio_claim_input(Rasp.handle, echo_pin)
        Rasp.used_pins.update([trig_pin, echo_pin])

        lgpio.gpio_write(Rasp.handle, trig_pin, 0)
        time.sleep(0.000002)
        lgpio.gpio_write(Rasp.handle, trig_pin, 1)
        time.sleep(0.00001)
        lgpio.gpio_write(Rasp.handle, trig_pin, 0)

        start_time = time.time()
        timeout_time = start_time + timeout_s

        while lgpio.gpio_read(Rasp.handle, echo_pin) == 0:
            if time.time() > timeout_time:
                return -1

        pulse_start = time.time()
        while lgpio.gpio_read(Rasp.handle, echo_pin) == 1:
            if time.time() > timeout_time:
                return -1

        pulse_end = time.time()
        elapsed = pulse_end - pulse_start
        distance_cm = (elapsed * 34300) / 2
        return distance_cm

    @staticmethod
    def ServoWrite(pin_num, angle):
        if not GPIOZERO_AVAILABLE:
            raise ImportError("gpiozero 라이브러리가 필요합니다. 'pip install gpiozero'로 설치해주세요.")
        
        if not (0 <= angle <= 180):
            raise ValueError("angle은 0~180 사이여야 합니다.")

        if pin_num not in Rasp.servos:
            # 일반적인 서보(SG90 등)는 0.5ms~2.5ms 펄스 폭에서 더 잘 작동할 수 있습니다.
            Rasp.servos[pin_num] = Servo(pin_num, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)

        # angle(0~180)을 gpiozero의 value(-1.0~1.0)로 변환
        value = (angle / 90.0) - 1.0
        Rasp.servos[pin_num].value = value
        Rasp.used_pins.add(pin_num)

    @staticmethod
    def ServoStop(pin_num):
        if pin_num in Rasp.servos:
            Rasp.servos[pin_num].detach()
            del Rasp.servos[pin_num]
        
        #念のためlgpio PWM도 중지
        if Rasp.handle is not None:
            try:
                lgpio.tx_pwm(Rasp.handle, pin_num, 0, 0)
            except lgpio.error:
                pass # PWM 핀이 아니면 에러 무시

    @staticmethod
    def RFID_Setup(bus=0, device=0):
        try:
            spi = spidev.SpiDev()
            spi.open(bus, device)
            Rasp.rfid_reader = MFRC522(spi)
            print("RFID 리더가 설정되었습니다.")
        except Exception as e:
            raise Exception(f"RFID 리더 설정 실패: {e}")

    @staticmethod
    def RFID_Read(as_string=True):
        if Rasp.rfid_reader is None:
            raise Exception("RFID 리더가 설정되지 않았습니다. RFID_Setup()을 먼저 호출해주세요.")
        
        (status, uid) = Rasp.rfid_reader.read_uid()
        
        if status == MFRC522.MI_OK:
            if as_string:
                return f"{uid[0]:02X}:{uid[1]:02X}:{uid[2]:02X}:{uid[3]:02X}"
            else:
                return uid
        return None

    @staticmethod
    def RFID_Close():
        if Rasp.rfid_reader is not None and hasattr(Rasp.rfid_reader, 'spi') and Rasp.rfid_reader.spi is not None:
            Rasp.rfid_reader.spi.close()
            Rasp.rfid_reader = None
            print("RFID 리더 연결이 해제되었습니다.")

    @staticmethod
    def Clean(all=False):
        # RFID 리더 정리
        Rasp.RFID_Close()

        # gpiozero 서보 정리
        if GPIOZERO_AVAILABLE:
            for pin in list(Rasp.servos.keys()):
                Rasp.servos[pin].detach()
            Rasp.servos.clear()

        # 기존 lgpio 정리
        if Rasp.handle is not None:
            pins_to_clean = range(0, 28) if all else list(Rasp.used_pins)
            
            for pin_num in pins_to_clean:
                try:
                    lgpio.tx_pwm(Rasp.handle, pin_num, 0, 0)
                except lgpio.error:
                    pass
                try:
                    lgpio.gpio_claim_output(Rasp.handle, pin_num)
                    lgpio.gpio_write(Rasp.handle, pin_num, 0)
                    lgpio.gpio_free(Rasp.handle, pin_num)
                except lgpio.error:
                    pass

            if not all:
                Rasp.used_pins.clear()

            lgpio.gpiochip_close(Rasp.handle)
            Rasp.handle = None

class Ard:
    def __init__(self, port="/dev/ttyACM0", baud=9600):
        self.ser = None
        self.used_pins = set()
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)
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