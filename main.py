import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from gtts import gTTS
import pychromecast
from pychromecast.controllers.media import MediaController
from slugify import slugify
from pydub import AudioSegment
import asyncio
import logging
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
ROOT_DIR = Path(__file__).parent
STATIC_DIR = ROOT_DIR / "static"
CACHE_DIR = STATIC_DIR / "cache"
CHROMECAST_NAME = "All"  # Edit this to your Google Home group name

# Ensure cache directory exists
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Load alarm sounds
alarm_sound_long = AudioSegment.from_mp3(STATIC_DIR / "emergency_alarm_long.mp3")
alarm_sound_short = AudioSegment.from_mp3(STATIC_DIR / "emergency_alarm_short.mp3")

# Global variable for the Chromecast device
cast = None

class CastListener:
    def __init__(self):
        self.discovered_devices = []

    def add_cast(self, uuid, service):
        self.discovered_devices.append(service)

async def discover_chromecast():
    global cast
    max_retries = 5
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            listener = CastListener()
            browser = await asyncio.to_thread(pychromecast.discovery.CastBrowser, listener)
            await asyncio.to_thread(browser.start_discovery)
            await asyncio.sleep(2)  # Give some time for discovery
            
            chromecasts, browser = await asyncio.to_thread(
                pychromecast.get_listed_chromecasts, friendly_names=[CHROMECAST_NAME]
            )
            if chromecasts:
                cast = chromecasts[0]
                await asyncio.to_thread(cast.wait)
                logger.info(f"Connected to Chromecast: {cast.name}")
                await asyncio.to_thread(browser.stop_discovery)
                return
            else:
                logger.warning(f"Chromecast '{CHROMECAST_NAME}' not found. Attempt {attempt + 1}/{max_retries}")
            
            await asyncio.to_thread(browser.stop_discovery)
        except Exception as e:
            logger.error(f"Error discovering Chromecast: {str(e)}")
        
        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)

    logger.error(f"Failed to discover Chromecast '{CHROMECAST_NAME}' after {max_retries} attempts")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: discover Chromecast
    await discover_chromecast()
    yield
    # Shutdown: clean up (if needed)
    if cast:
        await asyncio.to_thread(cast.disconnect)

app = FastAPI(lifespan=lifespan)

class TTSRequest(BaseModel):
    text: str
    lang: str = "en"
    slow: bool = False
    priority: int = 0

async def generate_tts(text: str, lang: str, slow: bool, priority: int) -> Path:
    filename = slugify(f"{text}-{lang}-{slow}-{priority}") + ".mp3"
    cache_file = CACHE_DIR / filename

    if not cache_file.is_file():
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(str(cache_file))
        logger.info(f"Generated TTS for text: {text}")

        if priority > 0:
            audio = AudioSegment.from_mp3(cache_file)
            amplified = audio + 10
            if priority == 1:
                amplified = alarm_sound_short + audio
            elif priority == 2:
                amplified = alarm_sound_long + audio
            elif priority == 3:
                amplified = alarm_sound_long + audio + alarm_sound_long

            amplified = amplified + 8
            amplified.export(cache_file, format='mp3')

        logger.info(f"Saved TTS file: {cache_file}")

    return cache_file


async def play_mp3(mp3_url: str, volume: Optional[float] = None):
    global cast
    if cast is None:
        raise HTTPException(status_code=503, detail="No Chromecast device available")

    logger.info(f"Attempting to play: {mp3_url}")
    try:
        await asyncio.to_thread(cast.wait)
        
        if volume is not None:
            await asyncio.to_thread(cast.set_volume, volume)

        mc = cast.media_controller
        await asyncio.to_thread(mc.play_media, mp3_url, 'audio/mp3')
        await asyncio.to_thread(mc.block_until_active)
        logger.info("Media playing command sent")
    except Exception as e:
        logger.error(f"Error playing media: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to play media")
    

@app.get("/static/{path:path}")
async def send_static(path: str):
    file_path = STATIC_DIR / path
    if file_path.is_file():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/play/{filename}")
async def play(filename: str, request: Request):
    mp3_file = STATIC_DIR / filename
    if mp3_file.is_file():
        mp3_url = f"{request.base_url}static/{filename}"
        await play_mp3(mp3_url)
        return {"status": "playing", "file": filename}
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/say")
async def say(tts_request: TTSRequest, request: Request):
    tts_file = await generate_tts(tts_request.text, tts_request.lang, tts_request.slow, tts_request.priority)
    mp3_url = f"{request.base_url}static/cache/{tts_file.name}"
    await play_mp3(mp3_url, volume=1 if tts_request.priority > 0 else None)
    return {"status": "playing", "text": tts_request.text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)