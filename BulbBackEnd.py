import sys
import asyncio
from quart import Quart, request, jsonify
from bleak import BleakClient, BleakScanner, BleakError
from bleak.exc import BleakError

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

    # Format: [Unknown, Red, Blue, Green]
    return bytearray([0x1, adjusted[0], adjusted[2], adjusted[1]])

class HueBulbClient:
    def __init__(self):
        self.client = None
        self.address = None

    async def connect(self):
        devices = await BleakScanner.discover()
        target_device = None

        for device in devices:
            print(f"Device found: {device.name}, {device.address}")
            if device.name == BULB_NAME:
                target_device = device
                break

        if target_device is None:
            print("Bulb not found.")
            return False

        self.address = target_device.address
        self.client = BleakClient(self.address)
        try:
            await self.client.connect()
            print(f"Connected to bulb: {self.address}")
            # On Windows, pairing might need to be handled separately
            # Ensure the device is paired via Windows Bluetooth settings
            return True
        except Exception as e:
            print(f"Failed to connect to bulb: {e}")
            return False

    async def write_color(self, rgb):
        if self.client is None or not self.client.is_connected:
            print("Client is not connected, attempting to reconnect...")
            connected = await self.connect()
            if not connected:
                print("Failed to reconnect to bulb.")
                return False
        color = convert_rgb(rgb)
        try:
            await self.client.write_gatt_char(COLOR_CHARACTERISTIC, color)
            print(f"Set color to {rgb}")
            return True
        except BleakError as e:
            print(f"Failed to write color to bulb: {e}")
            if 'Authentication required' in str(e):
                print("Authentication required. Please pair the device manually in Windows settings.")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False
    async def write_brightness(self, light_level):
        if self.client is None or not self.client.is_connected:
            print("Client is not connected, attempting to reconnect...")
            connected = await self.connect()
            if not connected:
                print("Failed to reconnect to bulb.")
                return False
        byte_light_level = bytearray([light_level,])
        try:
            await self.client.write_gatt_char(BRIGHTNESS_CHARACTERISTIC, byte_light_level)
            print(f"Set color to {light_level}")
            return True
        except BleakError as e:
            print(f"Failed to write light_level to bulb: {e}")
            if 'Authentication required' in str(e):
                print("Authentication required. Please pair the device manually in Windows settings.")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False
        

    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            print("Disconnected from bulb.")

# Initialize the bulb client
bulb_client = HueBulbClient()

app = Quart(__name__)

@app.before_serving
async def startup():
    connected = await bulb_client.connect()
    if not connected:
        print("Failed to connect to bulb")
        # Optionally, you can raise an exception or handle the failure as needed

@app.after_serving
async def shutdown():
    await bulb_client.disconnect()

@app.route('/set_color', methods=['POST'])
async def set_light_color():
    data = await request.get_json()
    rgb = data.get("rgb", [255, 255, 255])  # Default to white if no color provided

    success = await bulb_client.write_color(rgb)
    if success:
        return jsonify({"status": "success", "color": rgb})
    else:
        return jsonify({"status": "failed", "message": "Could not set color"}), 500
@app.route('/set_brightness', methods=['POST'])
async def set_light_color():
    data = await request.get_json()
    brightness = data.get("brightness", 100)  # Default to white if no color provided

    success = await bulb_client.write_brightness(brightness)
    if success:
        return jsonify({"status": "success", "brightness": brightness})
    else:
        return jsonify({"status": "failed", "message": "Could not set brightness"}), 500

if __name__ == '__main__':
    # On Windows, set the event loop policy for asyncio
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Run the app using an ASGI server
    # Since we're in __main__, we can use hypercorn's async runner
    import hypercorn.asyncio
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:5000"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
