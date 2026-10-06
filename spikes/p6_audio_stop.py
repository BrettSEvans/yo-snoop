"""Run, create a bot with websocket_settings.audio.url=ws://host.docker.internal:8788,
press Enter while it talks; a listener on a second device notes when sound stops."""
import asyncio, base64, json, os, sys, time
import websockets
from google.cloud import texttospeech
from spikes.common import SECRETS_DIR, pdt_now

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(SECRETS_DIR / "tts-key.json")
TEXT = ("Aight, peep this. This is a long test paragraph so we can measure how fast "
        "the audio stops. ") * 8
RATE = 16000
CHUNK = RATE * 2 // 10  # 100 ms of 16-bit mono

def synth() -> bytes:
    c = texttospeech.TextToSpeechClient()
    r = c.synthesize_speech(input=texttospeech.SynthesisInput(text=TEXT),
                            voice=texttospeech.VoiceSelectionParams(language_code="en-US"),
                            audio_config=texttospeech.AudioConfig(
                                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                                sample_rate_hertz=RATE))
    return r.audio_content[44:]  # strip WAV header

async def handler(ws):
    pcm = synth()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_reader(sys.stdin, stop.set)
    print("talking; press Enter to stop")
    for i in range(0, len(pcm), CHUNK):
        if stop.is_set():
            print(pdt_now(), "STOP SENT at", time.time()); break
        await ws.send(json.dumps({"trigger": "realtime_audio.bot_output",
                                  "data": {"chunk": base64.b64encode(pcm[i:i+CHUNK]).decode(),
                                           "sample_rate": RATE}}))
        await asyncio.sleep(0.1)  # real-time pacing: never run ahead of playback
    await asyncio.sleep(10)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8788):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
