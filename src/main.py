import flet as ft
import logging
from kv4p import Kv4pHTDevice

SETTINGS_KEY_PREFIX = "kv4p-app-state."
PRESETS_KEY_PREFIX = "kv4p-app-presets."

bleDevice = Kv4pHTDevice()


class FrequencyControlWidget(ft.Row):
    def __init__(self, key, text, client_storage):
        super().__init__()

        self.key = SETTINGS_KEY_PREFIX + key
        self.step = 0.0010
        self.client_storage = client_storage

        if not self.client_storage.contains_key(self.key):
            self.client_storage.set(self.key, 143.0000)

        self.btn_dec_freq = ft.Button(
            content=ft.Icon(ft.Icons.ARROW_BACK),
            on_click=self.handle_dec_freq,
        )
        self.txt_freq = ft.TextField(
            value=f"{self.client_storage.get(self.key):8.4f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            expand=True,
        )
        self.btn_inc_freq = ft.Button(
            content=ft.Icon(ft.Icons.ARROW_FORWARD),
            on_click=self.handle_inc_freq,
        )

        self.controls = [
            ft.Text(text),
            self.btn_dec_freq,
            self.txt_freq,
            self.btn_inc_freq,
        ]
        self.expand = True

    async def handle_dec_freq(self, e):
        value = await self.client_storage.get_async(self.key)
        await self.client_storage.set_async(self.key, round(value - self.step, 4))
        self.txt_freq.value = f"{await self.client_storage.get_async(self.key):8.4f}"
        self.update()
        await self.parent.tune()

    async def handle_inc_freq(self, e):
        value = await self.client_storage.get_async(self.key)
        await self.client_storage.set_async(self.key, round(value + self.step, 4))
        self.txt_freq.value = f"{await self.client_storage.get_async(self.key):8.4f}"
        self.update()
        await self.parent.tune()

    def set_value(self, value):
        self.txt_freq.value = f"{value:8.4f}"
        self.update()

    async def get_value(self):
        value = await self.client_storage.get_async(self.key)
        return value


class TuningWidget(ft.Column):
    def __init__(self, client_storage):
        super().__init__()

        self.key = SETTINGS_KEY_PREFIX + "rx_tx_split"
        self.client_storage = client_storage
        self.rx_freq = FrequencyControlWidget(
            "rx_freq", "Rx Frequency:", client_storage
        )
        self.tx_freq = FrequencyControlWidget(
            "tx_freq", "Tx Frequency:", client_storage
        )
        self.btn_split = ft.Switch("Split Tx Frequency", on_change=self.handle_split)

        if not self.client_storage.contains_key(self.key):
            self.client_storage.set(self.key, False)

        split = self.client_storage.get(self.key)
        if split:
            self.btn_split.icon = ft.Icons.LOCK_OPEN
            self.tx_freq.disabled = False
            self.tx_freq.visible = True
        else:
            self.btn_split.icon = ft.Icons.LOCK
            self.tx_freq.disabled = True
            self.tx_freq.visible = False

        self.w_tone = ToneWidget(client_storage)
        self.w_squelch = SquelchWidget(client_storage)
        self.w_bandwidth = BandwidthWidget(client_storage)

        self.controls = [
            self.rx_freq,
            self.btn_split,
            self.tx_freq,
            self.w_bandwidth,
            self.w_tone,
            self.w_squelch,
        ]

    async def handle_split(self, e):
        value = e.control.value
        self.client_storage.set(self.key, value)

        if value:
            self.tx_freq.disabled = False
            self.tx_freq.visible = True
        else:
            self.tx_freq.disabled = True
            self.tx_freq.visible = False

        self.tx_freq.set_value(await self.rx_freq.get_value())
        self.update()

    async def tune(self):
        await bleDevice.cmd_tune_to(
            await self.tx_freq.get_value(),
            await self.rx_freq.get_value(),
            await self.w_tone.get_value(),
            await self.w_squelch.get_value(),
            await self.w_bandwidth.get_value(),
        )


class BandwidthWidget(ft.Row):
    def __init__(self, client_storate):
        super().__init__()

        self.key = SETTINGS_KEY_PREFIX + "bandwidth"
        self.client_storage = client_storate

        if not self.client_storage.contains_key(self.key):
            self.client_storage.set(self.key, "N")

        self.dd_bandwidth = ft.Dropdown(
            value=self.client_storage.get(self.key),
            options=[
                ft.dropdown.Option("N", "Narrow"),
                ft.dropdown.Option("W", "Wide"),
            ],
        )

        self.controls = [
            ft.Text("Bandwidth"),
            self.dd_bandwidth,
        ]

    def handle_tone(self, e):
        logging.info("setting bandwidth: %d", int(self.dd_bandwidth.value))

        self.client_storage.set(self.key, self.dd_bandwidth.value)

    async def get_value(self):
        value = await self.client_storage.get_async(self.key)
        return value


class FiltersWidget(ft.Row):
    def __init__(self, client_storage):
        super().__init__()

        self.key = SETTINGS_KEY_PREFIX + "filters_"
        self.client_storage = client_storage

        if not self.client_storage.contains_key(self.key + "pre"):
            self.client_storage.set(self.key + "pre", False)

        if not self.client_storage.contains_key(self.key + "high"):
            self.client_storage.set(self.key + "high", False)

        if not self.client_storage.contains_key(self.key + "low"):
            self.client_storage.set(self.key + "low", False)

        self.sw_pre = ft.Switch(
            "Pre",
            value=self.client_storage.get(self.key + "pre"),
            on_change=self.handle_filters,
        )
        self.sw_high = ft.Switch(
            "High",
            value=self.client_storage.get(self.key + "high"),
            on_change=self.handle_filters,
        )
        self.sw_low = ft.Switch(
            "Low",
            value=self.client_storage.get(self.key + "low"),
            on_change=self.handle_filters,
        )

        self.controls = [
            ft.Text("Filters"),
            self.sw_pre,
            self.sw_high,
            self.sw_low,
        ]

    def get_filters(self):
        pre = self.client_storage.get(self.key + "pre")
        high = self.client_storage.get(self.key + "high")
        low = self.client_storage.get(self.key + "low")

        return {
            "pre": pre,
            "high": high,
            "low": low,
        }

    async def handle_filters(self, e):
        logging.info(
            "setting filters pre: %d high: %d low: %d",
            self.sw_pre.value,
            self.sw_high.value,
            self.sw_low.value,
        )

        await self.client_storage.set_async(self.key + "pre", self.sw_pre.value)
        await self.client_storage.set_async(self.key + "high", self.sw_high.value)
        await self.client_storage.set_async(self.key + "low", self.sw_low.value)

        await bleDevice.cmd_filters(
            self.sw_pre.value,
            self.sw_high.value,
            self.sw_low.value,
        )


ctcss_tone_list = [
    67.0,
    71.9,
    74.4,
    77.0,
    79.7,
    82.5,
    85.4,
    88.5,
    91.5,
    94.8,
    97.4,
    100.0,
    103.5,
    107.2,
    110.9,
    114.8,
    118.8,
    123.0,
    127.3,
    131.8,
    136.5,
    141.3,
    146.2,
    151.4,
    156.7,
    162.2,
    167.9,
    173.8,
    179.9,
    186.2,
    192.8,
    203.5,
    210.7,
    218.1,
    225.7,
    233.6,
    241.8,
    250.3,
]


class ToneWidget(ft.Row):
    def __init__(self, client_storage):
        super().__init__()

        self.key = SETTINGS_KEY_PREFIX + "ctcss_tone"
        self.client_storage = client_storage

        if not self.client_storage.contains_key(self.key):
            self.client_storage.set(self.key, 0)

        self.dd_tone = ft.Dropdown(
            value=self.client_storage.get(self.key),
            options=[ft.dropdown.Option("0", "None")],
            width=100,
            on_change=self.handle_tone,
        )

        for i, v in enumerate(ctcss_tone_list):
            self.dd_tone.options.append(ft.dropdown.Option(f"{i:d}", f"{v:.1f} Mhz"))

        self.dd_tone.value = self.client_storage.get(self.key)

        self.controls = [
            ft.Text("CTCSS Tone"),
            self.dd_tone,
        ]

    async def get_value(self):
        value = await self.client_storage.get_async(self.key)
        return int(value)

    def handle_tone(self, e):
        logging.info("setting tone: %d", int(self.dd_tone.value))

        self.client_storage.set(self.key, self.dd_tone.value)


class SquelchWidget(ft.Row):
    def __init__(self, client_storage):
        super().__init__()

        self.key = SETTINGS_KEY_PREFIX + "gain"
        self.client_storage = client_storage

        if not self.client_storage.contains_key(self.key):
            self.client_storage.set(self.key, 4)

        self.dd_squelch = ft.Dropdown(
            value=self.client_storage.get(self.key),
            options=[],
            width=100,
            on_change=self.handle_squelch,
        )

        for x in range(1, 9):
            self.dd_squelch.options.append(ft.dropdown.Option(f"{x:d}"))

        self.dd_squelch.value = self.client_storage.get(self.key)

        self.controls = [
            ft.Text("Gain"),
            self.dd_squelch,
        ]

    async def get_value(self):
        value = await self.client_storage.get_async(self.key)
        return value

    def handle_squelch(self, e):
        logging.info("setting gain: %d", int(self.dd_squelch.value))

        self.client_storage.set(self.key, self.dd_squelch.value)


class PTTWidget(ft.Row):
    def __init__(self):
        super().__init__()

        gd = ft.GestureDetector(
            content=ft.ElevatedButton(
                content=ft.Row([ft.Icon(ft.Icons.MIC), ft.Text("Push to Talk")]),
                on_click=self.handle_ptt_up,
            ),
            on_tap_down=self.handle_ptt_down,
            on_tap_up=self.handle_ptt_up,
        )

        btn_stop = ft.ElevatedButton(
            content=ft.Row([ft.Icon(ft.Icons.MULTIPLE_STOP), ft.Text("Stop")]),
            on_click=self.handle_stop,
        )

        self.controls = [gd, btn_stop]

    async def handle_ptt_down(self, e):
        logging.info("push-to-talk down")
        await bleDevice.cmd_ptt_down()

    async def handle_ptt_up(self, e):
        logging.info("push-to-talk up")
        await bleDevice.cmd_ptt_up()

    async def handle_stop(self, e):
        logging.info("stop")
        await bleDevice.cmd_stop()


class SavePresetWidget(ft.Row):
    def __init__(self, client_storage):
        super().__init__()

        self.client_storage = client_storage

        self.txt_name = ft.TextField("", expand=True)
        self.btn_save = ft.Button(
            "Save Preset",
            on_click=self.handle_save_preset,
        )
        self.controls = [
            ft.Row(
                [
                    ft.Text("Preset Name"),
                    self.txt_name,
                    self.btn_save,
                ],
                expand=True,
            ),
        ]

    def handle_save_preset(self, e):
        if self.txt_name.value == "":
            dlg = ft.AlertDialog(title=ft.Text("Preset name cannot be empty"))
            self.page.open(dlg)

        keys = self.client_storage.get_keys(SETTINGS_KEY_PREFIX)
        preset = {}
        for k in keys:
            preset[k.replace(SETTINGS_KEY_PREFIX, "")] = self.client_storage.get(k)

        logging.info("saving preset: %s", preset)
        self.client_storage.set(PRESETS_KEY_PREFIX + self.txt_name.value, preset)


class PresetsListWidget(ft.Column):
    def __init__(self, client_storage):
        super().__init__()

        self.client_storage = client_storage

        self.set_items()

    def set_items(self):
        self.controls.clear()

        keys = self.client_storage.get_keys(PRESETS_KEY_PREFIX)
        for k in keys:
            preset = self.client_storage.get(k)

            summary = ""
            if preset["rx_tx_split"]:
                summary += f"Rx: %s Mhz " % (preset["rx_freq"])
                summary += f"Tx: %s Mhz " % (preset["tx_freq"])
                summary += f"CTCSS: %s " % (preset["ctcss_tone"])
            else:
                summary += f"Rx: %s Mhz " % (preset["rx_freq"])
                summary += f"Tx: %s Mhz " % (preset["rx_freq"])
                summary += f"CTCSS: %s " % (preset["ctcss_tone"])

            print(preset["rx_tx_split"])
            self.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.ListTile(
                                    title=ft.Text(k.replace(PRESETS_KEY_PREFIX, "")),
                                    subtitle=ft.Text(summary),
                                ),
                                ft.Row(
                                    [
                                        ft.TextButton("Load"),
                                        ft.TextButton(
                                            "Delete",
                                            on_click=self.handle_delete,
                                            data=k,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.END,
                                ),
                            ]
                        ),
                        expand=True,
                    )
                )
            )

    def handle_delete(self, e):
        self.client_storage.remove(e.control.data)
        self.set_items()
        self.update()


def main(page):
    page.adaptive = True

    async def handle_connect(e):
        await bleDevice.connect()
        btn_connect.text = "Disconnect"
        page.update()

    btn_connect = ft.Button("Connect", on_click=handle_connect)
    page.appbar = ft.AppBar(
        title=ft.Text("kv4p HT"),
        actions=[btn_connect],
    )

    def talk_view():
        return ft.SafeArea(
            ft.Column(
                [
                    TuningWidget(page.client_storage),
                    FiltersWidget(page.client_storage),
                    PTTWidget(),
                    SavePresetWidget(page.client_storage),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )

    def presets_view():
        return ft.SafeArea(
            PresetsListWidget(page.client_storage),
            expand=True,
        )

    def handle_nav_change(e):
        if e.control.selected_index == 0:
            page.controls = [talk_view()]
        elif e.control.selected_index == 1:
            page.title = "Presets"
            page.controls = [presets_view()]
        elif e.control.selected_index == 2:
            page.title = "Settings!"
            page.controls = [ft.Text("Settings!")]
        page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.RECORD_VOICE_OVER, label="Talk"),
            ft.NavigationBarDestination(
                icon=ft.Icons.BOOKMARK_BORDER,
                selected_icon=ft.Icons.BOOKMARK,
                label="Presets",
            ),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Settings"),
        ],
        border=ft.Border(
            top=ft.BorderSide(color=ft.CupertinoColors.SYSTEM_GREY2, width=0)
        ),
        on_change=handle_nav_change,
    )

    page.add(talk_view())


logging.basicConfig(level=logging.INFO)
ft.app(main)
