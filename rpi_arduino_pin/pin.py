import lgpio
import serial
import time
import threading

class Rasp:
    handle = None
    used_pins = set()  # 사용한 핀 기록

    @staticmethod
    def Setup(chip=0):
        if Rasp.handle is None:
            Rasp.handle = lgpio.gpiochip_open(chip)
        else:
            raise Exception("이미 GPIO handle이 열려있습니다.")

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
        time.sleep(0.00001)  # 10us 트리거 신호
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
        """
        지정된 핀에 연결된 서보 모터를 angle (0~180도)만큼 회전시킵니다.
        lgpio의 PWM 기능을 사용합니다. (50Hz)
        """
        if not (0 <= angle <= 180):
            raise ValueError("angle은 0~180 사이여야 합니다.")

        # 서보 펄스 폭(500us~2500us)을 듀티 사이클(0~100%)로 변환
        # 50Hz 주파수의 주기: 20000us
        pulse_width_us = 500.0 + (angle / 180.0) * 2000.0
        duty_cycle = (pulse_width_us / 20000.0) * 100.0

        lgpio.tx_pwm(Rasp.handle, pin_num, 50, duty_cycle)
        Rasp.used_pins.add(pin_num)

    @staticmethod
    def ServoStop(pin_num):
        """
        지정된 핀의 PWM 출력을 중지하여 서보 모터를 정지시킵니다.
        """
        # 듀티 사이클을 0으로 설정하여 PWM 신호를 중지
        try:
            lgpio.tx_pwm(Rasp.handle, pin_num, 50, 0)
        except lgpio.error:
            pass # 핀이 PWM 모드가 아니어도 오류 없음

    @staticmethod
    def Clean(all=False):
        """
        핸들 닫기 + 사용 핀 해제
        """
        if Rasp.handle is not None:
            pins_to_clean = range(0, 28) if all else list(Rasp.used_pins)
            
            for pin_num in pins_to_clean:
                try:
                    # 실행 중일 수 있는 PWM 중지
                    lgpio.tx_pwm(Rasp.handle, pin_num, 50, 0)
                    # 핀을 출력으로 설정하고 0으로 초기화
                    lgpio.gpio_claim_output(Rasp.handle, pin_num)
                    lgpio.gpio_write(Rasp.handle, pin_num, 0)
                    lgpio.gpio_free(Rasp.handle, pin_num)
                except lgpio.error:
                    pass  # 사용 불가능하거나 이미 해제된 핀 무시
            
            if not all:
                Rasp.used_pins.clear()

            lgpio.gpiochip_close(Rasp.handle)
            Rasp.handle = None

class Ard:
    def __init__(self, port="/dev/ttyACM0", baud=9600):
        self.ser = None
        self.used_pins = set()
        self._interrupt_callbacks = {}
        self._stop_thread = threading.Event()
        self._read_thread = None
        self.Setup(port, baud)

    def Setup(self, port, baud):
        if self.ser is None:
            self.ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)  # 아두이노 초기화 대기
            self._start_read_thread()
        else:
            raise Exception("이미 시리얼 연결이 열려있습니다.")

    def _start_read_thread(self):
        if self._read_thread is None or not self._read_thread.is_alive():
            self._stop_thread.clear()
            self._read_thread = threading.Thread(target=self._read_serial_data, daemon=True)
            self._read_thread.start()

    def _read_serial_data(self):
        while not self._stop_thread.is_set():
            try:
                if self.ser and self.ser.in_waiting > 0:
                    line = self.ser.readline().decode().strip()
                    if line.startswith("INTERRUPT"):
                        parts = line.split()
                        if len(parts) == 3:
                            pin = int(parts[1])
                            value = int(parts[2])
                            if pin in self._interrupt_callbacks:
                                self._interrupt_callbacks[pin](pin, value)
                    # 다른 비동기 메시지 처리 (예: 에러 응답 등)
                    # print(f"Arduino: {line}") # 디버깅용
            except Exception as e:
                # 시리얼 포트 오류 처리
                print(f"Error reading from serial: {e}")
                break
            time.sleep(0.01) # CPU 사용량 줄이기

    def _send_command(self, cmd):
        if self.ser is None:
            raise Exception("Arduino가 Setup 되지 않았습니다.")
        self.ser.write((cmd + "\n").encode())

    def _receive_response(self):
        if self.ser is None:
            raise Exception("Arduino가 Setup 되지 않았습니다.")
        return self.ser.readline().decode().strip()

    def Write(self, pin_num, value):
        self._send_command(f"PINMODE {pin_num} OUTPUT")
        if isinstance(value, int):
            value = "HIGH" if value else "LOW"
        elif str(value).strip() == "1":
            value = "HIGH"
        elif str(value).strip() == "0":
            value = "LOW"

        self._send_command(f"DWRITE {pin_num} {value}")
        self.used_pins.add(pin_num)

    def Read(self, pin_num):
        self._send_command(f"PINMODE {pin_num} INPUT")
        self._send_command(f"DREAD {pin_num}")
        val = self._receive_response()
        self.used_pins.add(pin_num)
        return val

    def AnalogWrite(self, pin_num, value):
        self._send_command(f"PINMODE {pin_num} OUTPUT") # 아날로그 출력도 핀모드 설정 필요
        self._send_command(f"AWRITE {pin_num} {value}")
        self.used_pins.add(pin_num)

    def AnalogRead(self, pin_num):
        self._send_command(f"PINMODE {pin_num} INPUT")
        self._send_command(f"AREAD {pin_num}")
        val = self._receive_response()
        self.used_pins.add(pin_num)
        return val

    def ServoWrite(self, pin_num, angle):
        if not (0 <= angle <= 180):
            raise ValueError("angle은 0~180 사이여야 합니다.")
        self._send_command(f"SERVOWRITE {pin_num} {angle}")
        self.used_pins.add(pin_num)

    def ServoStop(self, pin_num):
        self._send_command(f"SERVOSTOP {pin_num}")
        self.used_pins.add(pin_num)

    def Edge(self, pin_num, mode, callback):
        """
        아두이노 핀에 인터럽트를 설정하고 콜백 함수를 등록합니다.
        mode: "RISING", "FALLING", "BOTH"
        callback: 인터럽트 발생 시 호출될 함수 (인자: pin_num, value)
        """
        if mode not in ["RISING", "FALLING", "BOTH"]:
            raise ValueError("mode는 RISING, FALLING, BOTH 중 하나여야 합니다.")
        
        self._send_command(f"ATTACH_INTERRUPT {pin_num} {mode}")
        response = self._receive_response()
        if response.startswith("OK"): # 아두이노로부터 성공 응답을 받으면 콜백 등록
            self._interrupt_callbacks[pin_num] = callback
            self.used_pins.add(pin_num)
        else:
            raise Exception(f"Failed to attach interrupt: {response}")

    def DetachEdge(self, pin_num):
        """
        아두이노 핀에서 인터럽트를 해제합니다.
        """
        self._send_command(f"DETACH_INTERRUPT {pin_num}")
        response = self._receive_response()
        if response.startswith("OK"): # 아두이노로부터 성공 응답을 받으면 콜백 해제
            if pin_num in self._interrupt_callbacks:
                del self._interrupt_callbacks[pin_num]
            self.used_pins.discard(pin_num)
        else:
            raise Exception(f"Failed to detach interrupt: {response}")

    def Clean(self):
        """
        아두이노에 연결된 모든 서보 모터를 해제하고 시리얼 연결을 닫습니다.
        등록된 모든 인터럽트도 해제합니다.
        """
        if self.ser is not None:
            # 모든 인터럽트 해제
            for pin_num in list(self._interrupt_callbacks.keys()):
                try:
                    self.DetachEdge(pin_num)
                except Exception as e:
                
                    print(f"Error detaching interrupt for pin {pin_num}: {e}")

            self._send_command("CLEANALLSERVOS") # 아두이노에 모든 서보 해제 명령 전송
            self._receive_response() # 아두이노의 응답을 기다림 (OK: All servos detached)
            
            self._stop_thread.set() # 스레드 중지 신호
            if self._read_thread and self._read_thread.is_alive():
                self._read_thread.join(timeout=1) # 스레드 종료 대기

            self.ser.close()
            self.ser = None
            self.used_pins.clear()
