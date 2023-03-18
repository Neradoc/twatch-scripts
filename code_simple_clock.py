from digitalio import DigitalInOut, Pull
import displayio
import board
import microcontroller
import os
import rtc
import socketpool
import ssl
import terminalio
import time
import wifi
from rainbowio import colorwheel

import adafruit_ntp
from adafruit_display_text.bitmap_label import Label

from axp202 import AXP202, IRQ
axp202 = AXP202(board.I2C())
axp202.set_ldo2(True)
irq_axp = DigitalInOut(board.AXP202_INT)

buz = DigitalInOut(board.VIBRATE)
buz.switch_to_output(False)

# irq_touch = DigitalInOut(board.TOUCH_INT)

def do_buz(durée):
    buz.value = True
    time.sleep(0.01 * durée)
    buz.value = False

######################################################################

display = board.DISPLAY
display.brightness = 0.2
dark_mode = True

splash = displayio.Group()
font0 = font1 = terminalio.FONT

name_label = Label(
    text="Connecting...", font=font1, color=0x00FFFF, scale=2,
    anchored_position=(display.width // 2, 4), anchor_point=(0.5, 0),
)
date_label = Label(
    text="21/10/2015", font=font0, color=0x0080FF, scale=3,
    anchored_position=(display.width // 2, display.height // 2), anchor_point=(0.5, 0.5),
)
time_label = Label(
    text="12:00:00", font=font0, color=0x00FF00, scale=3,
    anchored_position=(display.width // 2, display.height), anchor_point=(0.5, 1),
)

splash.append(name_label)
splash.append(date_label)
splash.append(time_label)
display.show(splash)

display.auto_refresh = False
display.refresh()

######################################################################

name_label.text = "Clock !"

socket_pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(socket_pool, tz_offset=1)
rtc.RTC().datetime = ntp.datetime

######################################################################

"""Formats of date and time."""
# US
# format_date = "{month}/{day:02d}/{year}"
# format_time = "{hour_12}:{minute:02d}:{second:02d} {am_pm}"
# others
format_date = "{day}/{month:02d}/{year}"
format_time = "{hour}:{minute:02d}:{second:02d}"

######################################################################

color = [colorwheel(x) for x in range(0,255,24)]
cur_color = 0

def do_buttons():
    global dark_mode, cur_color
    if not irq_axp.value:
        irqs = axp202.get_irqs()
        if IRQ.SHORT_PRESS in irqs:
            # print("Short press")
            do_buz(10)
            date_label.color = color[cur_color]
            display.refresh()
            cur_color += 1
        if IRQ.LONG_PRESS in irqs:
            # print("Long press")
            if dark_mode:
                display.brightness = 1.0
            else:
                display.brightness = 0.2
            dark_mode = not dark_mode
            do_buz(10)

######################################################################

now = time.localtime()
now_dict = {}

while True:
    now = time.localtime()
    now_dict["year"] = now.tm_year
    now_dict["yy"] = now.tm_year % 100  # year on 2 digits
    now_dict["day"] = now.tm_mday
    now_dict["weekday"] = now.tm_wday
    now_dict["yearday"] = now.tm_yday
    now_dict["month"] = now.tm_mon
    now_dict["hour"] = now.tm_hour
    now_dict["minute"] = now.tm_min
    now_dict["second"] = now.tm_sec
    now_dict["hour_12"] = now.tm_hour
    now_dict["am_pm"] = "AM"

    if now.tm_hour >= 12:
        now_dict["hour_12"] = now.tm_hour - 12
        now_dict["am_pm"] = "PM"  # AM is the default
    if now_dict["hour_12"] == 0:
        now_dict["hour_12"] = 12

    date_string = format_date.format(**now_dict)
    time_string = format_time.format(**now_dict)

    date_label.text = date_string
    time_label.text = time_string
    display.refresh()

    print(date_string, time_string)

    if now.tm_sec == 0:
        do_buz(5)

    # reconnect maybe if needed (does nothing otherwise)
    wifi.radio.connect(
        os.getenv("CIRCUITPY_WIFI_SSID"),
        os.getenv("CIRCUITPY_WIFI_PASSWORD")
    )

    # wait until the second changes to try to be as close to it as possible
    while time.localtime().tm_sec == now.tm_sec:
        do_buttons()
        time.sleep(0.02)
