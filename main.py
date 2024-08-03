import asyncio
from fastapi import FastAPI, HTTPException
import pychromecast
from pychromecast.controllers.media import MediaController

# Constants
CHROMECAST_NAME = "All"  # Edit this to your Google Home group name
ALARM_SOUND_URL = "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars60.wav"  # Replace with your desired remote audio URL

app = FastAPI()

# Global variable for the Chromecast device
cast = None

async def discover_chromecast():
    global cast
    chromecasts, _ = await asyncio.to_thread(pychromecast.get_listed_chromecasts, friendly_names=[CHROMECAST_NAME])
    if chromecasts:
        cast = chromecasts[0]
        await asyncio.to_thread(cast.wait)
    else:
        raise Exception(f"Chromecast '{CHROMECAST_NAME}' not found")

@app.on_event("startup")
async def startup_event():
    await discover_chromecast()

async def play_alarm():
    if cast is None:
        raise HTTPException(status_code=503, detail="No Chromecast device available")

    try:
        await asyncio.to_thread(cast.wait)
        mc = cast.media_controller
        await asyncio.to_thread(cast.set_volume, 1)  # Set volume to maximum
        await asyncio.to_thread(mc.play_media, ALARM_SOUND_URL, 'audio/wav')
        await asyncio.to_thread(mc.block_until_active)
        return {"status": "success", "message": "Alarm triggered successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/trigger_alarm")
@app.get("/trigger_alarm")
async def trigger_alarm():
    result = await play_alarm()
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.get("/health")
async def health_check():
    if cast is None:
        raise HTTPException(status_code=503, detail="Chromecast not connected")
    return {"status": "healthy", "chromecast": cast.name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)