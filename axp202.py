import time
from micropython import const
from adafruit_bus_device.i2c_device import I2CDevice

# tft_backlight
AXP_PASS = 1
AXP_FAIL = 0

_APX202_ADDRESS = const(0x35)
_AXP202_LDO2 = const(2)
_AXP202_ON  = const(1)
_AXP202_OFF = const(0)
_AXP202_DCDC3 = const(1)
_AXP202_IC_TYPE = const(0x03)
_AXP202_LDO234_DC23_CTL = const(0x12)
_AXP202_INTSTS1 = const(0x48)

AXP202_CHIP_ID = 0x41
AXP192_CHIP_ID = 0x03

class IRQ:
    CHARGING = 1
    CHARGING_DONE = 2
    VBUS_REMOVE = 3
    LONG_PRESS = 4
    SHORT_PRESS = 5

class AXP202:
    def __init__(self, i2c, address=_APX202_ADDRESS):
        self.device = I2CDevice(i2c, address)
        self.buffer = bytearray(2)
        self.chip_id = 0
        self._outputReg = 0
        self.init()

    def init(self):
        self.chip_id = self._readByte(_AXP202_IC_TYPE, 1)[0]
        if self.chip_id in (AXP202_CHIP_ID, AXP192_CHIP_ID):
            self._outputReg = self._readByte(_AXP202_LDO234_DC23_CTL, 1)[0]
            return AXP_PASS
        # raise ?
        return AXP_FAIL

    def _readByte(self, reg, num):
        self.buffer[0] = reg
        with self.device as bus:
            bus.write_then_readinto(self.buffer, self.buffer, out_end=1, in_start=1, in_end=num+1)
        return self.buffer[1:num+1]

    def _writeByte(self, reg, buf):
        self.buffer[0] = reg
        self.buffer[1:len(buf)+1] = buf
        with self.device as bus:
            bus.write(self.buffer, end=len(buf)+1)

    def set_ldo2(self, en):
        # setPowerOutPut(ch=AXP202_LDO2,en)
        data = 0
        while data == 0:
            # timeout and raise ?
            data = self._readByte(_AXP202_LDO234_DC23_CTL, 1)[0]
            time.sleep(0.001)
    
        ch = _AXP202_LDO2
        if en:
            data |= 1 << ch
        else:
            data &= ~(1 << ch)
    
        # FORCED_OPEN_DCDC3
        data |= (_AXP202_ON << _AXP202_DCDC3)

        self._writeByte(_AXP202_LDO234_DC23_CTL, bytes([data]))
        time.sleep(0.001)
        val = self._readByte(_AXP202_LDO234_DC23_CTL, 1)[0]

        if data == val:
            self._outputReg = val
            return AXP_PASS

        return AXP_FAIL

    def readIRQ(self):
        self.irq = bytearray(5)
        for i in range(5):
            self.irq[i:i+1] = self._readByte(_AXP202_INTSTS1 + i, 1)

    def clearIRQ(self):
        val = bytes([0xFF])
        for i in range(5):
            self._writeByte(_AXP202_INTSTS1 + i, val)

    def isVbusRemoveIRQ(self):
        return bool(self.irq[0] & (1 << 2))
    def isChargingIRQ(self):
        return bool(self.irq[1] & (1 << 3))
    def isChargingDoneIRQ(self):
        return bool(self.irq[1] & (1 << 2))
    def isPEKShortPressIRQ(self):
        return bool(self.irq[2] & (1 << 1))
    def isPEKLongtPressIRQ(self):
        return bool(self.irq[2] & (1))

    def get_irqs(self):
        irqs = []
        self.readIRQ()
        if self.isChargingIRQ():
            irqs.append(IRQ.CHARGING)
        if self.isChargingDoneIRQ():
            irqs.append(IRQ.CHARGING_DONE)
        if self.isVbusRemoveIRQ():
            irqs.append(IRQ.VBUS_REMOVE)
        if self.isPEKLongtPressIRQ():
            irqs.append(IRQ.LONG_PRESS)
        if self.isPEKShortPressIRQ():
            irqs.append(IRQ.SHORT_PRESS)
        self.clearIRQ()
        return irqs

    @property
    def backlight(self):
        return bool(self._outputReg & (1 << AXP202_LDO2))

    @backlight.setter
    def backlight(self, value):
        ret = self.set_ldo2(value)

