from flask import Flask, request
import socket
import pychromecast
import logging
from gtts import gTTS
from slugify import slugify
from pathlib import Path
from urllib.parse import urlparse
from pydub import AudioSegment
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

root_dir = os.path.dirname(os.path.abspath(__file__))

alarm_sound_long = AudioSegment.from_mp3(root_dir + "/static/emergency_alarm_long.mp3")
alarm_sound_short = AudioSegment.from_mp3(root_dir + "/static/emergency_alarm_short.mp3")


app = Flask(__name__)
logging.info("Starting up chromecasts")

#search chromecast by name
chromecast_name = "Google Home" #edit me to be your google home group
chromecasts, _ = pychromecast.get_chromecasts()
cast = next(cc for cc in chromecasts if cc.device.friendly_name == chromecast_name)

#or use a fixed ip address
#cast = pychromecast.Chromecast('192.168.1.100')

def play_tts(text, lang='en', slow=False, priority=0):
    filename = slugify(text+"-"+lang+"-"+str(slow)+"-"+str(priority)) + ".mp3"
    path = "/static/cache/"
    cache_filename = root_dir + path + filename
    tts_file = Path(cache_filename)
    error = False

    if not tts_file.is_file():
        try:
            tts = gTTS(text=text, lang=lang, slow=slow)
            logging.info(tts)
            tts.save(cache_filename)
            if priority > 0:
                file = AudioSegment.from_mp3(cache_filename)
                amplified = file + 10
                if priority is 1:
                    amplified = alarm_sound_short + file
                if priority is 2:
                    amplified = alarm_sound_long + file
                if priority is 3:
                    amplified = alarm_sound_long + file + alarm_sound_long

                amplified = amplified + 8
                amplified.export(cache_filename, format='mp3')
        except:
            error = True
            if priority > 0:
                filename = "emergency_alarm_long.mp3"
            else:
                filename = "empty.mp3"


    urlparts = urlparse(request.url)
    if error:
        mp3_url = "http://" +urlparts.netloc + "/static/" + filename 
    else:
        mp3_url = "http://" +urlparts.netloc + path + filename 

    logging.info(mp3_url)
    if priority > 0:
        play_mp3(mp3_url, volume=1)
    else:
        play_mp3(mp3_url)


def play_mp3(mp3_url, volume=None):
    print(mp3_url)
    cast.wait()
    
    if volume is not None:
        cast.set_volume(volume)

    mc = cast.media_controller
    mc.play_media(mp3_url, 'audio/mp3')

@app.route('/static/<path:path>')
def send_static(path):
        return send_from_directory('static', path)

@app.route('/play/<filename>')
def play(filename):
    urlparts = urlparse(request.url)
    mp3 = Path(root_dir + "/static/"+filename)
    if mp3.is_file():
        play_mp3("http://"+urlparts.netloc+"/static/"+filename)
        return filename
    else:
        return "False"

@app.route('/say/')
def say():
    text = request.args.get("text")
    lang = request.args.get("lang")
    if not text:
        return False
    if not lang:
        lang = "it"
    play_tts(text, lang=lang)
    return text

@app.route('/alarm/')
def alarm():
    text = request.args.get("text")
    lang = request.args.get("lang")
    priority = request.args.get("priority")

    if not text:
        return False
    if not lang:
        lang = "it"
    if not priority:
        priority = 1
    
    priority=int(priority)

    play_tts(text, lang=lang, priority=priority)
    return text

if __name__ == '__main__':
        app.run(debug=True,host='0.0.0.0', port=5001)
