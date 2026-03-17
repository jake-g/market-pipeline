import asyncio
import json
import logging

import websockets

logging.basicConfig(level=logging.INFO)


async def test_ais():
  url = "wss://stream.aisstream.io/v0/stream"
  try:
    async with websockets.connect(url, ping_interval=None) as ws:
      subscribe_message = {
          "APIKey": "e3d9ba0013f6b6da6546ae1e9ff1e337e7cbfa2b",
          "BoundingBoxes": [[[-90, -180], [90, 180]]]  # Global view for testing
      }
      await ws.send(json.dumps(subscribe_message))
      logging.info("Connected and sent subscription")

      # Wait for 1 message then exit
      response = await asyncio.wait_for(ws.recv(), timeout=10.0)
      data = json.loads(response)
      logging.info(f"Received valid message: {data['MessageType']}")
      print(json.dumps(data, indent=2))
      return True

  except Exception as e:
    logging.error(f"Failed to connect: {e}")
    return False


if __name__ == "__main__":
  asyncio.run(test_ais())
