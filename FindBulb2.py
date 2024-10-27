import asyncio
from bleak import BleakScanner, BleakClient

# Replace with the name of your bulb as it appears in scans
BULB_NAME = "Hue color lamp"

LIGHT_CHARACTERISTIC = "932c32bd-0002-47a2-835a-a8d455b859dd"
BRIGHTNESS_CHARACTERISTIC = "932c32bd-0003-47a2-835a-a8d455b859dd"
TEMPERATURE_CHARACTERISTIC = "932c32bd-0004-47a2-835a-a8d455b859dd"
COLOR_CHARACTERISTIC = "932c32bd-0005-47a2-835a-a8d455b859dd"


def convert_rgb(rgb):
    scale = 0xFF
    adjusted = [max(1, chan) for chan in rgb]
    total = sum(adjusted)
    adjusted = [int(round(chan / total * scale)) for chan in adjusted]

    # Unknown, Red, Blue, Green
    return bytearray([0x1, adjusted[0], adjusted[2], adjusted[1]])

async def main():
    # Scan for devices
    devices = await BleakScanner.discover()
    target_device = None

    # Find the device by name
    for device in devices:
        print(f"Device found: {device.name}, {device.address}")
        if device.name == BULB_NAME:
            target_device = device
            break

    if target_device is None:
        print("Bulb not found.")
        return

    # Connect to the bulb using its address found from scanning
    async with BleakClient(target_device.address) as client:
        paired = await client.pair(protection_level=2)
        print(f"Paired: {paired}")

        print("Turning Light off...")
        await client.write_gatt_char(LIGHT_CHARACTERISTIC, b"\x00", response=False)
        await asyncio.sleep(1.0)
        print("Turning Light on...")
        await client.write_gatt_char(LIGHT_CHARACTERISTIC, b"\x01", response=False)
        await asyncio.sleep(1.0)

        print("Setting color to RED...")
        color = convert_rgb([255, 0, 0])
        await client.write_gatt_char(COLOR_CHARACTERISTIC, color, response=False)
        await asyncio.sleep(1.0)

        print("Setting color to GREEN...")
        color = convert_rgb([0, 255, 0])
        await client.write_gatt_char(COLOR_CHARACTERISTIC, color, response=False)
        await asyncio.sleep(1.0)

        print("Setting color to BLUE...")
        color = convert_rgb([0, 0, 255])
        await client.write_gatt_char(COLOR_CHARACTERISTIC, color, response=False)
        await asyncio.sleep(1.0)

        for brightness in range(256):
            print(f"Set Brightness to {brightness}...")
            await client.write_gatt_char(
                BRIGHTNESS_CHARACTERISTIC,
                bytearray(
                    [
                        brightness,
                    ]
                ),
                response=False,
            )
            await asyncio.sleep(0.2)

        print(f"Set Brightness to {40}...")
        await client.write_gatt_char(
            BRIGHTNESS_CHARACTERISTIC,
            bytearray(
                [
                    40,
                ]
            ),
            response=False,
        )


asyncio.run(main())
