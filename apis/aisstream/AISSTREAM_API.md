# 🚢 AISStream.io API Integration Guide

The **AISStream.io API** provides free, real-time access to global maritime AIS (Automatic Identification System) data via WebSockets.

* **Real-Time Only:** Unlike commercial REST APIs, AISStream does *not* offer historical data endpoints.
* **WebSocket Streaming:** Data is pushed continuously as a massive firehose. For pipeline integration, we sample this stream locally to calculate point-in-time congestion metrics.

---

## 🔑 1. How to Get an API Key
All connections require a free API key. Because AISStream actively blocks cross-origin browser requests (CORS), your keys must be kept secure and all API consumption must occur backend-side.

1. **Authenticate:** Go to [AISStream.io](https://aisstream.io/) and sign in using a GitHub account.
2. **Generate Key:** Navigate to the[API Keys page](https://aisstream.io/apikeys) and create a new key.
3. **Configure Environment:** Add the key to your pipeline's `.env` file:
   ```env
   AISSTREAM_API_KEY="your_api_key_here"
   ```

---

## 🚦 2. Connection Rules & Limitations
*To maintain a stable connection and avoid being forcibly disconnected by the server, you must adhere to these rules:*

* **The 3-Second Rule:** You must send your initial JSON subscription payload within **3 seconds** of opening the WebSocket connection. Otherwise, the server will drop you.
* **The TCP Queue Limit (Throttling):** The global AIS firehose is massive. If your client script cannot process incoming messages fast enough (e.g., ~300+ msgs/sec), the server's TCP queue will fill up and you will be disconnected.
* **Mitigation:** Always use **`BoundingBoxes`** and **`FilterMessageTypes`** to strictly constrain the data you receive.
* **Dynamic Updates:** You can change your active filters at any time by sending a new subscription payload over the *existing* WebSocket connection. It will instantly overwrite the previous state.

---

## 📡 3. Subscription Payload Mechanics

**Endpoint:** `wss://stream.aisstream.io/v0/stream`

To start receiving data, send a JSON subscription message immediately upon connection.
* **Bounding Boxes:** Formatted as an array of areas: `[[[Lat1, Lon1], [Lat2, Lon2]]]`. Overlapping boxes do *not* generate duplicate messages.

### Example Subscription JSON:
```json
{
   "APIKey": "<YOUR_API_KEY>",
   "BoundingBoxes": [
       [[26.2, 56.1],[26.8, 56.6]],   // Strait of Hormuz
       [[23.5, 119.5], [25.0, 121.0]]  // Taiwan Strait
   ],
   "FilterMessageTypes":[
       "PositionReport",
       "ShipStaticData"
   ]
}
```

---

## 🗂 4. Core Message Types & Schema

All incoming data is returned as JSON. AISStream injects a highly useful `MetaData` block into every packet, meaning you get the ship's Name, MMSI, and Location even if the raw binary AIS packet didn't explicitly include it.

### Standard Message Envelope
```json
{
  "MessageType": "PositionReport",
  "MetaData": {
    "MMSI": 259000420,
    "ShipName": "AUGUSTSON",
    "latitude": 66.02695,
    "longitude": 12.253821666666,
    "time_utc": "2022-12-29 18:22:32.318353 +0000 UTC"
  },
  "Message": { ... } // Contains the specific MessageType payload
}
```

### Key Message Types to Filter For
| Message Type | Description | Key Attributes |
| :--- | :--- | :--- |
| `PositionReport` | Standard Class A commercial vessels reporting location. | `Sog` (Speed), `Cog` (Course), `TrueHeading`, `NavigationalStatus` |
| `StandardClassBPositionReport` | Class B vessels (smaller boats, fishing, local tankers). | Similar to Class A, lower broadcast priority. |
| `ShipStaticData` | Broadcast every few mins. Contains fixed ship identifiers. | `Name`, `CallSign`, `Dimension` (A/B/C/D), `Type` (Cargo=70-79, Tanker=80-89) |
| `AidsToNavigationReport` | Marks buoys, lighthouses, and hazards. | `Name`, `OffPosition`, `VirtualAtoN`, `Type` |
| `SafetyBroadcastMessage` | Emergency alerts or urgent hazard warnings. | `Text` (e.g., `"CRASH... POS:22^18N"`) |

*(Note: Free tier schemas are marked as beta by AISStream and keys may occasionally drift).*

---

## 💻 5. Quick Start Example (Python)

Below is an `asyncio` script demonstrating how the pipeline connects to the stream, subscribes to specific chokepoints, samples the firehose for 20 seconds, deduplicates vessels, and gracefully closes.

*Requires: `pip install websockets`*

```python
import asyncio
import websockets
import json

API_KEY = "YOUR_API_KEY_HERE"
SAMPLE_DURATION = 20  # Seconds to listen before aggregating

async def fetch_vessel_sample():
    uri = "wss://stream.aisstream.io/v0/stream"

    # 1. Define payload for desired chokepoints
    subscription_payload = {
        "APIKey": API_KEY,
        "BoundingBoxes": [
            [[26.2, 56.1], [26.8, 56.6]],   # Strait of Hormuz
            [[8.8, -79.6], [9.4, -79.9]]    # Panama Canal
        ],
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
    }

    unique_ships = {}

    try:
        # 2. Connect to WebSocket
        async with websockets.connect(uri) as websocket:

            # 3. Send subscription within 3 seconds!
            await websocket.send(json.dumps(subscription_payload))
            print("Connected and subscribed. Sampling data...")

            # 4. Listen for the defined duration
            end_time = asyncio.get_event_loop().time() + SAMPLE_DURATION
            while asyncio.get_event_loop().time() < end_time:

                # Fetch message with a short timeout to allow loop exit
                try:
                    msg_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(msg_str)

                    # 5. Extract MetaData and deduplicate by MMSI
                    meta = data.get("MetaData", {})
                    mmsi = meta.get("MMSI")

                    if mmsi and mmsi not in unique_ships:
                        unique_ships[mmsi] = meta
                        print(f"Detected: {meta.get('ShipName', 'Unknown')} at ({meta.get('latitude')}, {meta.get('longitude')})")

                except asyncio.TimeoutError:
                    continue # Standard timeout, just loop again

    except Exception as e:
        print(f"WebSocket Error: {e}")

    # 6. Aggregate results (Pipeline step)
    print(f"\n--- Sampling Complete ---")
    print(f"Total Unique Vessels Tracked: {len(unique_ships)}")
    return unique_ships

# Run the pipeline fetcher
if __name__ == "__main__":
    asyncio.run(fetch_vessel_sample())
```
