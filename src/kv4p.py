import asyncio
import logging
from ble_serial.bluetooth.ble_client import BLE_client

COMMAND_HEADER = bytearray(
    [
        0xFF,
        0x00,
        0xFF,
        0x00,
        0xFF,
        0x00,
        0xFF,
        0x00,
    ]
)


class BleDevice:
    def __init__(self):
        ADAPTER = None
        SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
        WRITE_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
        READ_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
        DEVICE = "kv4p HT"
        WRITE_WITH_RESPONSE = False

        self.ble = BLE_client(ADAPTER, "ID")
        self.ble.set_receiver(self.receive_callback)

    async def connect(
        self, device, service_uuid, write_uuid, read_uuid, write_with_response
    ):
        try:
            await self.ble.connect(device, "public", service_uuid, 10.0)
            await self.ble.setup_chars(write_uuid, read_uuid, "rw", write_with_response)

            await asyncio.gather(
                self.ble.send_loop(), self.cmd_get_firmware_ver(self.ble, "v")
            )
        finally:
            await self.ble.disconnect()

    def cmd_ptt_down():
        data = COMMAND_HEADER + bytearray([0x01])
        logging.debug("sending ptt_down", data)

    def cmd_ptt_up():
        data = COMMAND_HEADER + bytearray([0x02])
        logging.debug("sending ptt_up", data)

    def cmd_tune_to(
        self, tx_freq: float, rx_freq: float, tone: int, squelch: int, bandwidth: str
    ):
        tx_band = check_frequency_range(tx_freq)
        rx_band = check_frequency_range(rx_freq)

        if not tx_band or not rx_band:
            return 1

        if tone < 0 or tone > 22:
            return 1

        if squelch < 1 or squelch > 8:
            return 1

        if bandwidth != "w" or bandwidth != "n":
            return 1

        data = (
            COMMAND_HEADER
            + bytearray([0x03])
            + bytearray([f"{tx_freq:8.4f}"])
            + bytearray([f"{rx_freq:8.4f}"])
            + bytearray([f"{tone:02d}"])
            + bytearray([f"{squelch:d}"])
            + bytearray([f"{bandwidth}"])
        )
        logging.debug("sending tune_to", data)

    def cmd_filters(self, emphasis: bool, high: bool, low: bool):
        data = COMMAND_HEADER + bytearray([0x04]) + bytearray([emphasis, high, low])
        logging.debug("sending filters", data)

    def cmd_stop():
        data = COMMAND_HEADER + bytearray([0x05])
        logging.debug("sending stop", data)

    def cmd_get_firmware_ver(self, band: str):
        if band != "u" or band != "v":
            return 1

        data = COMMAND_HEADER + bytearray([0x06]) + bytearray([band])
        logging.debug("sending get_firmware_ver", data)

    def receive_callback(value: bytes):
        logging.debug("received:", value)

    def send_audio():
        pass

    def receive_audio():
        pass


def check_frequency_range(n):
    if 134.0000 <= n <= 174.0000:
        return "v"  # VHF
    elif 400.0000 <= n <= 480.0000:
        return "u"  # UHF
    else:
        return None  # Out of range
