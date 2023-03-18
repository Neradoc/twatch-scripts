# import code_simple_clock

from digitalio import *
import board
import time

from axp202 import AXP202, IRQ
axp202 = AXP202(board.I2C())
axp202.set_ldo2(True)

irq_axp = DigitalInOut(board.AXP202_INT)

while True:
    if not irq_axp.value:
        irqs = axp202.get_irqs()
        if IRQ.SHORT_PRESS in irqs:
            print("Short press")
        if IRQ.LONG_PRESS in irqs:
            print("Long press")
    time.sleep(0.1)

