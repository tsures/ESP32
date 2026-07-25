from machine import Pin, I2C
import onewire
import ds18x20
import ssd1306
import time

# DS18B20
TEMP_PIN = 14
one_wire = onewire.OneWire(Pin(TEMP_PIN))
sensor = ds18x20.DS18X20(one_wire)

roms = sensor.scan()

if not roms:
    raise RuntimeError("No DS18B20 sensor found")

print("DS18B20 found:", roms)

# OLED: SDA = GPIO21, SCL = GPIO22
i2c = I2C(
    0,
    sda=Pin(21),
    scl=Pin(22),
    freq=400000
)

print("I2C devices:", i2c.scan())

oled = ssd1306.SSD1306_I2C(128, 64, i2c)


def show_temperature(temperature):
    oled.fill(0)

    oled.text("TEMPERATURE", 16, 8)
    oled.text("{:.1f} C".format(temperature), 32, 30)
    oled.text("DS18B20", 32, 50)

    oled.show()


while True:
    try:
        # Start temperature conversion
        sensor.convert_temp()

        # DS18B20 needs about 750 ms
        time.sleep_ms(750)

        temperature = sensor.read_temp(roms[0])

        print("Temperature: {:.2f} C".format(temperature))
        show_temperature(temperature)

    except Exception as error:
        print("Temperature error:", error)

        oled.fill(0)
        oled.text("SENSOR ERROR", 12, 25)
        oled.show()

    time.sleep(2)