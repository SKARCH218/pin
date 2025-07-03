import lgpio
import serial
import time
import threading
import asyncio
import serial_asyncio
import pigpio # Added

# --- Constants ---
SPEED_OF_SOUND_CM_S = 34300
TRIGGER_PULSE_DELAY = 0.000002
TRIGGER_PULSE_WIDTH = 0.00001

PWM_FREQUENCY_HZ = 50
SERVO_MIN_PULSE_WIDTH_US = 500.0
SERVO_PULSE_RANGE_US = 2000.0
SERVO_MAX_ANGLE = 180.0
PWM_PERIOD_US = 1_000_000 / PWM_FREQUENCY_HZ

class Rasp:
    """
    Controls Raspberry Pi GPIO, I2C, and SPI using the lgpio library.
    lgpio 라이브러리를 사용하여 라즈베리파이의 GPIO, I2C, SPI를 제어합니다.
    """
    def __init__(self, chip=0, i2c_bus=1, spi_channel=0):
        self.handle = lgpio.gpiochip_open(chip)
        self.used_pins = set()
        self.i2c_handle = None
        self.spi_handle = None
        self._i2c_bus = i2c_bus
        self._spi_channel = spi_channel
        self.pi = pigpio.pi() # Added
        if not self.pi.connected: # Added
            raise Exception("pigpio daemon not connected! Run 'sudo pigpiod'") # Added

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.Clean()

    # --- GPIO Methods ---
    def Read(self, pin_num):
        lgpio.gpio_claim_input(self.handle, pin_num)
        self.used_pins.add(pin_num)
        return lgpio.gpio_read(self.handle, pin_num)

    def Write(self, pin_num, value):
        lgpio.gpio_claim_output(self.handle, pin_num)
        lgpio.gpio_write(self.handle, pin_num, value)
        self.used_pins.add(pin_num)

    def Free(self, pin_num):
        lgpio.gpio_free(self.handle, pin_num)
        self.used_pins.discard(pin_num)

    # --- PWM Methods (using pigpio) ---
    def pwm_start(self, pin_num, duty_cycle, frequency=PWM_FREQUENCY_HZ):
        """
        Starts PWM on a pin with a given duty cycle and frequency using pigpio.
        주어진 듀티 사이클과 주파수로 핀에서 PWM을 시작합니다 (pigpio 사용).
        """
        self.pi.set_PWM_frequency(pin_num, frequency)
        self.pi.set_PWM_dutycycle(pin_num, int(255 * duty_cycle / 100)) # pigpio uses 0-255 for duty cycle
        self.used_pins.add(pin_num)

    def pwm_stop(self, pin_num):
        """
        Stops PWM on a pin using pigpio.
        핀의 PWM을 중지합니다 (pigpio 사용).
        """
        self.pi.set_PWM_dutycycle(pin_num, 0)

    def ServoWrite(self, pin_num, angle):
        if not (0 <= angle <= SERVO_MAX_ANGLE):
            raise ValueError(f"Angle must be between 0 and {int(SERVO_MAX_ANGLE)}.")
        # pigpio uses microseconds for servo pulses
        pulse_width_us = int(SERVO_MIN_PULSE_WIDTH_US + (angle / SERVO_MAX_ANGLE) * SERVO_PULSE_RANGE_US)
        self.pi.set_servo_pulsewidth(pin_num, pulse_width_us)
        self.used_pins.add(pin_num)

    def ServoStop(self, pin_num):
        self.pi.set_servo_pulsewidth(pin_num, 0) # Stop servo by setting pulsewidth to 0

    # --- I2C Methods ---
    def _open_i2c(self, device_addr):
        if self.i2c_handle is None:
            self.i2c_handle = lgpio.i2c_open(self._i2c_bus, device_addr)

    def i2c_write_byte(self, device_addr, data):
        self._open_i2c(device_addr)
        lgpio.i2c_write_byte(self.i2c_handle, data)

    def i2c_read_byte(self, device_addr):
        self._open_i2c(device_addr)
        return lgpio.i2c_read_byte(self.i2c_handle)

    def i2c_write_device(self, device_addr, data):
        self._open_i2c(device_addr)
        lgpio.i2c_write_device(self.i2c_handle, data)

    def i2c_read_device(self, device_addr, count):
        self._open_i2c(device_addr)
        _, data = lgpio.i2c_read_device(self.i2c_handle, count)
        return data

    # --- SPI Methods ---
    def _open_spi(self, spi_flags=0, spi_baud=1000000):
        if self.spi_handle is None:
            self.spi_handle = lgpio.spi_open(self._spi_channel, spi_baud, spi_flags)

    def spi_xfer(self, data, spi_flags=0, spi_baud=1000000):
        self._open_spi(spi_flags, spi_baud)
        _, rx_data = lgpio.spi_xfer(self.spi_handle, data)
        return rx_data

    def Clean(self, all_pins=False):
        if self.handle is not None:
            pins_to_clean = range(0, 28) if all_pins else list(self.used_pins)
            for pin_num in pins_to_clean:
                try:
                    self.pwm_stop(pin_num)
                    lgpio.gpio_claim_output(self.handle, pin_num)
                    lgpio.gpio_write(self.handle, pin_num, 0)
                    lgpio.gpio_free(self.handle, pin_num)
                except lgpio.error:
                    pass
            if not all_pins:
                self.used_pins.clear()
            lgpio.gpiochip_close(self.handle)
            self.handle = None
        if self.i2c_handle is not None:
            lgpio.i2c_close(self.i2c_handle)
            self.i2c_handle = None
        if self.spi_handle is not None:
            lgpio.spi_close(self.spi_handle)
            self.spi_handle = None
        if self.pi is not None: # Added
            self.pi.stop() # Added
            self.pi = None # Added

class Ard:
    """
    Communicates with an Arduino over serial for various controls.
    시리얼을 통해 아두이노와 통신하여 다양한 제어를 수행합니다.
    """
    def __init__(self, port="/dev/ttyACM0", baud=9600, timeout=1):
        self.ser = serial.Serial(port, baud, timeout=timeout)
        time.sleep(2)
        self.used_pins = set()
        self._interrupt_callbacks = {}
        self._stop_thread = threading.Event()
        self._read_thread = threading.Thread(target=self._read_serial_data, daemon=True)
        self._read_thread.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.Clean()

    def _read_serial_data(self):
        while not self._stop_thread.is_set():
            try:
                if self.ser and self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith("INTERRUPT"):
                        parts = line.split()
                        if len(parts) == 3:
                            pin, value = int(parts[1]), int(parts[2])
                            if pin in self._interrupt_callbacks:
                                self._interrupt_callbacks[pin](pin, value)
            except (serial.SerialException, OSError) as e:
                print(f"Error reading from serial port: {e}")
                break
            time.sleep(0.01)

    def _send_command(self, cmd):
        if not self.ser or not self.ser.is_open:
            raise serial.SerialException("Arduino is not connected.")
        self.ser.write((cmd + "\n").encode('utf-8'))

    def _receive_response(self):
        if not self.ser or not self.ser.is_open:
            raise serial.SerialException("Arduino is not connected.")
        return self.ser.readline().decode('utf-8', errors='ignore').strip()

    # --- I2C Methods ---
    def i2c_write(self, addr, data):
        """
        Writes data to an I2C device via Arduino.
        아두이노를 통해 I2C 장치에 데이터를 씁니다.
        """
        if isinstance(data, list):
            data_str = ' '.join(map(str, data))
        else:
            data_str = str(data)
        self._send_command(f"I2CWRITE {addr} {data_str}")
        return self._receive_response()

    def i2c_read(self, addr, count):
        """
        Reads data from an I2C device via Arduino.
        아두이노를 통해 I2C 장치에서 데이터를 읽습니다.
        """
        self._send_command(f"I2CREAD {addr} {count}")
        response = self._receive_response()
        return [int(b) for b in response.split()]

    def Clean(self):
        if self.ser is not None and self.ser.is_open:
            self._send_command("CLEANALL")
            self._receive_response()
            self._stop_thread.set()
            if self._read_thread and self._read_thread.is_alive():
                self._read_thread.join(timeout=1)
            self.ser.close()
        self.ser = None

class AsyncArd:
    """
    Asynchronous version of the Ard class using asyncio.
    asyncio를 사용하는 Ard 클래스의 비동기 버전입니다.
    """
    def __init__(self):
        self.reader = None
        self.writer = None

    async def connect(self, port="/dev/ttyACM0", baud=9600):
        self.reader, self.writer = await serial_asyncio.open_serial_connection(url=port, baudrate=baud)
        await asyncio.sleep(2) # Wait for Arduino to initialize

    async def _send_command(self, cmd):
        if not self.writer:
            raise ConnectionError("Not connected to Arduino")
        self.writer.write((cmd + "\n").encode('utf-8'))
        await self.writer.drain()

    async def _receive_response(self):
        if not self.reader:
            raise ConnectionError("Not connected to Arduino")
        return (await self.reader.readline()).decode('utf-8', errors='ignore').strip()

    async def Write(self, pin_num, value):
        state = "HIGH" if value else "LOW"
        await self._send_command(f"DWRITE {pin_num} {state}")

    async def Read(self, pin_num):
        await self._send_command(f"DREAD {pin_num}")
        return await self._receive_response()

    async def AnalogWrite(self, pin_num, value):
        await self._send_command(f"AWRITE {pin_num} {value}")

    async def AnalogRead(self, pin_num):
        await self._send_command(f"AREAD {pin_num}")
        return await self._receive_response()

    async def close(self):
        if self.writer:
            await self._send_command("CLEANALL")
            self.writer.close()
            await self.writer.wait_closed()