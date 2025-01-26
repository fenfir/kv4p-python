import asyncio
import logging
from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
import asyncio
import sys
from itertools import count, takewhile
from typing import Iterator

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

COMMAND_HEADER = bytearray([0xDE, 0xAD, 0xBE, 0xEF, 0xDE, 0xAD, 0xBE, 0xEF])


UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"


def sliced(data: bytes, n: int) -> Iterator[bytes]:
    """
    Slices *data* into chunks of size *n*. The last slice may be smaller than
    *n*.
    """
    return takewhile(len, (data[i : i + n] for i in count(0, n)))


def match_nus_uuid(device: BLEDevice, adv: AdvertisementData):
    # This assumes that the device includes the UART service UUID in the
    # advertising data. This test may need to be adjusted depending on the
    # actual advertising data supplied by the device.
    if UART_SERVICE_UUID.lower() in adv.service_uuids:
        return True

    return False


class Kv4pHTDevice:
    def __init__(self):
        self.rx_char = None
        self.device = None
        self.nus = None
        self.client = None

    async def connect(self):
        self.device = await BleakScanner.find_device_by_filter(match_nus_uuid)
        if self.device is None:
            logging.warning(
                "no matching device found, you may need to edit match_nus_uuid()."
            )
            return False

        logging.info("Connecting to device %s", self.device)

        self.client = BleakClient(
            self.device,
            disconnected_callback=self.handle_disconnect,
        )
        await self.client.connect()

        await self.client.start_notify(UART_TX_CHAR_UUID, self.handle_rx)
        logging.info("Connected to device: %s", self.device)
        self.nus = self.client.services.get_service(UART_SERVICE_UUID)
        self.rx_char = self.nus.get_characteristic(UART_RX_CHAR_UUID)

    def match_nus_uuid(device: BLEDevice, adv: AdvertisementData):
        # This assumes that the device includes the UART service UUID in the
        # advertising data. This test may need to be adjusted depending on the
        # actual advertising data supplied by the device.
        if UART_SERVICE_UUID.lower() in adv.service_uuids:
            return True

        return False

    def handle_disconnect(self, _: BleakClient):
        logging.info("Disconnected to device: %s", self.device)
        self.rx_char = None
        self.device = None
        self.nus = None
        self.client = None

    def handle_rx(self, _: BleakGATTCharacteristic, data: bytearray):
        print("received:", data)
        pass

    async def send_data(self, data: bytearray):
        for s in sliced(data, self.rx_char.max_write_without_response_size):
            await self.client.write_gatt_char(self.rx_char, s, response=False)

    async def cmd_ptt_down(self):
        data = COMMAND_HEADER + bytearray([0x01])
        logging.debug("sending ptt_down")
        await self.send_data(data)

    async def cmd_ptt_up(self):
        data = COMMAND_HEADER + bytearray([0x02])
        logging.debug("sending ptt_up")
        await self.send_data(data)

    async def cmd_tune_to(
        self,
        tx_freq: float,
        rx_freq: float,
        tone: int,
        squelch: int,
        bandwidth: str,
    ):
        tx_band = check_frequency_range(tx_freq)
        rx_band = check_frequency_range(rx_freq)

        # if not tx_band or not rx_band:
        #     return 1

        # if tone < 0 or tone > 22:
        #     return 1

        # if squelch < 1 or squelch > 8:
        #     return 1

        # if bandwidth != "w" or bandwidth != "n":
        #     return 1

        data = (
            COMMAND_HEADER
            + bytearray([0x03])
            + bytearray(f"{tx_freq:8.4f}".encode(encoding="ASCII"))
            + bytearray(f"{rx_freq:8.4f}".encode(encoding="ASCII"))
            + bytearray(f"{tone:02d}".encode(encoding="ASCII"))
            + bytearray(f"{squelch:d}".encode(encoding="ASCII"))
            + bytearray(f"{bandwidth}".encode(encoding="ASCII"))
        )
        logging.debug("sending tune_to", data)
        await self.send_data(data)

    async def cmd_filters(self, emphasis: bool, high: bool, low: bool):
        data = (
            COMMAND_HEADER
            + bytearray([0x04])
            + bytearray(f"{emphasis:1d}".encode(encoding="ASCII"))
            + bytearray(f"{high:1d}".encode(encoding="ASCII"))
            + bytearray(f"{low:1d}".encode(encoding="ASCII"))
        )
        logging.debug("sending filters")
        await self.send_data(data)

    async def cmd_stop(self):
        data = COMMAND_HEADER + bytearray([0x05])
        logging.debug("sending stop")
        await self.send_data(data)

    async def cmd_get_firmware_ver(self, band: str):
        if band != "u" or band != "v":
            return 1

        data = (
            COMMAND_HEADER
            + bytearray([0x06])
            + bytearray(band.encode(encoding="ASCII"))
        )
        logging.debug("sending get_firmware_ver")
        await self.send_data(data)

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
