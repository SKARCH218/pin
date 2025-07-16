from RPLCD.i2c import CharLCD

class I2cLcd:
    """I2C 인터페이스를 사용하여 LCD를 제어하는 클래스"""

    def __init__(self, address, port, expander='PCF8574', cols=16, rows=2):
        """
        클래스를 초기화하고 I2C LCD를 설정합니다.

        :param address: LCD의 I2C 주소 (예: 0x27)
        :param port: I2C 버스 번호 (예: 1)
        :param expander: I2C 익스팬더 칩 이름
        :param cols: LCD의 열 수
        :param rows: LCD의 행 수
        """
        self.lcd = CharLCD(
            i2c_expander=expander,
            address=address,
            port=port,
            cols=cols,
            rows=rows,
            charmap='A02',
            auto_linebreaks=True
        )
        print(f"I2C LCD initialized at address {hex(address)} on port {port}.")
        self.lcd.clear()

    def lcd_print(self, line1, line2=""):
        """
        LCD 화면에 텍스트를 출력합니다.

        :param line1: 첫 번째 줄에 표시할 텍스트
        :param line2: 두 번째 줄에 표시할 텍스트 (선택 사항)
        """
        self.lcd.clear()
        self.lcd.write_string(line1)
        if line2:
            self.lcd.cursor_pos = (1, 0)  # 두 번째 줄로 이동
            self.lcd.write_string(line2)

    def cleanup(self):
        """LCD를 끄고 정리합니다."""
        print("Closing LCD...")
        self.lcd.close(clear=True)