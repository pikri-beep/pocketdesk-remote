"""
PocketDesk Remote v2.0 - Senior Full-Stack & Windows Desktop Automation Backend
Built with FastAPI, Uvicorn, WebSockets, PyAutoGUI, PyCaw, Screen Brightness Control, PyTTSx3, and Win32 APIs.
"""

import os
import sys
import re
import io
import time
import socket
import ctypes
import platform
import threading
import subprocess
import urllib.parse
import asyncio
from typing import List, Optional

# Set console output encoding to UTF-8 for clean QR code & logs in Windows terminal
try:
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import httpx
import psutil
import qrcode
import pyperclip
import pyautogui
from PIL import Image

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Initialize PyAutoGUI settings for ultra-responsive remote control
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.0

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DROP_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "PocketDesk_Drop")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(DROP_DIR, exist_ok=True)

app = FastAPI(
    title="PocketDesk Remote v2.0",
    description="All-in-One Local Desktop Remote Controller for Windows",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------------------------
# Helper Utilities
# ---------------------------------------------------------------------------

def get_local_ip() -> str:
    """Retrieve the primary local LAN/Wi-Fi IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_volume_controller():
    """Retrieve PyCaw Master Volume Controller with thread-safe COM init and fallback."""
    try:
        import comtypes
        comtypes.CoInitialize()
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        speakers = AudioUtilities.GetSpeakers()
        if hasattr(speakers, 'EndpointVolume'):
            return speakers.EndpointVolume
        interface = speakers.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
        return interface.QueryInterface(IAudioEndpointVolume)
    except Exception as e:
        print(f"[Audio] PyCaw Audio Controller Init Note: {e}")
        return None


def get_system_volume() -> dict:
    """Read Windows master volume level and mute status."""
    vol_ctrl = get_volume_controller()
    if vol_ctrl:
        try:
            scalar = vol_ctrl.GetMasterVolumeLevelScalar()
            mute = bool(vol_ctrl.GetMute())
            return {"volume": int(round(scalar * 100)), "mute": mute, "supported": True}
        except Exception as e:
            print(f"[Audio] Error reading volume: {e}")
    # Fallback response
    return {"volume": 50, "mute": False, "supported": False}


def set_system_volume(level: int) -> bool:
    """Set Windows master volume level (0-100)."""
    vol_ctrl = get_volume_controller()
    if vol_ctrl:
        try:
            target = max(0.0, min(1.0, level / 100.0))
            vol_ctrl.SetMasterVolumeLevelScalar(target, None)
            return True
        except Exception as e:
            print(f"[Audio] Error setting volume via PyCaw: {e}")
    # Fallback to PyAutoGUI key simulation
    try:
        # Step adjust
        pyautogui.press('volumeup' if level > 50 else 'volumedown', _pause=False)
        return True
    except Exception:
        return False


def toggle_system_mute(mute_state: Optional[bool] = None) -> bool:
    """Toggle or explicitly set mute status."""
    vol_ctrl = get_volume_controller()
    if vol_ctrl:
        try:
            current_mute = bool(vol_ctrl.GetMute())
            target_mute = not current_mute if mute_state is None else mute_state
            vol_ctrl.SetMute(int(target_mute), None)
            return target_mute
        except Exception as e:
            print(f"[Audio] Error toggling mute via PyCaw: {e}")
    try:
        pyautogui.press('volumemute', _pause=False)
        return False
    except Exception:
        return False


def get_system_brightness() -> int:
    """Read Windows display brightness (0-100%)."""
    try:
        import screen_brightness_control as sbc
        b = sbc.get_brightness()
        if isinstance(b, list) and len(b) > 0:
            return int(b[0])
        elif isinstance(b, (int, float)):
            return int(b)
        return 50
    except Exception as e:
        print(f"[Brightness] Read notice: {e}")
        return 50


def set_system_brightness(val: int) -> bool:
    """Set Windows display brightness (0-100%)."""
    try:
        import screen_brightness_control as sbc
        clamped = max(0, min(100, int(val)))
        sbc.set_brightness(clamped)
        return True
    except Exception as e:
        print(f"[Brightness] Set notice: {e}")
        return False


def capture_screenshot() -> Image.Image:
    """Capture live screenshot using PIL ImageGrab, MSS, or fallback placeholder."""
    # Method 1: PIL ImageGrab (standard Windows desktop grab)
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        if img:
            return img
    except Exception:
        pass

    # Method 2: MSS
    try:
        import mss
        with mss.MSS() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            if img:
                return img
    except Exception:
        pass

    # Method 3: Visual fallback canvas (when desktop is locked or DC is non-interactive)
    from PIL import ImageDraw
    canvas = Image.new("RGB", (1280, 720), color=(15, 23, 42))
    draw = ImageDraw.Draw(canvas)
    msg = "Layar Laptop Terkunci / Monitor Mati\nBuka kunci atau sentuh touchpad untuk mengaktifkan kembali."
    draw.text((120, 320), msg, fill=(148, 163, 184))
    return canvas


def launch_browser_url(url: str):
    """Launch target URL in Google Chrome if installed, or fallback to default browser."""
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            try:
                subprocess.Popen([path, url])
                return True
            except Exception:
                pass
    import webbrowser
    webbrowser.open(url)
    return True


def speak_worker(text: str):
    """Background worker for pyttsx3 Text-To-Speech with thread-safe COM handling."""
    try:
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        pass
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print(f"[TTS] Worker error: {e}")


# ---------------------------------------------------------------------------
# Pydantic Request Models
# ---------------------------------------------------------------------------

class VolumeRequest(BaseModel):
    volume: int

class VolumeStepRequest(BaseModel):
    delta: int

class MuteRequest(BaseModel):
    mute: Optional[bool] = None

class BrightnessRequest(BaseModel):
    brightness: int

class TextRequest(BaseModel):
    text: str

class KeyRequest(BaseModel):
    key: str

class ShortcutRequest(BaseModel):
    shortcut: str

class SearchRequest(BaseModel):
    query: str

class MessageRequest(BaseModel):
    message: str

class MouseClickRequest(BaseModel):
    button: str = "left"

class MouseScrollRequest(BaseModel):
    direction: str = "down"
    amount: int = 120

class ScreenClickRequest(BaseModel):
    x: float = 0.0
    y: float = 0.0
    button: str = "left"
    clicks: int = 1


class JarvisMessageRequest(BaseModel):
    text: str
    audio_target: Optional[str] = "laptop"


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_landing():
    """Serve the landing page for QR code scanning and manual IP input."""
    landing_file = os.path.join(STATIC_DIR, "landing.html")
    if os.path.exists(landing_file):
        with open(landing_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    # Fallback to index if landing.html is not present
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>PocketDesk Remote v2.0</h1><p>Halaman tidak ditemukan.</p>")


@app.get("/landing", response_class=HTMLResponse)
async def serve_landing_explicit():
    """Explicit route for landing page."""
    landing_file = os.path.join(STATIC_DIR, "landing.html")
    if os.path.exists(landing_file):
        with open(landing_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>PocketDesk Remote v2.0</h1><p>landing.html tidak ditemukan.</p>")


@app.get("/remote", response_class=HTMLResponse)
async def serve_remote():
    """Serve the single-page mobile remote controller."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>PocketDesk Remote v2.0</h1><p>index.html tidak ditemukan.</p>")


@app.get("/api/qrcode")
async def get_qrcode_image(url: Optional[str] = None):
    """Generate dynamic high-res PNG QR code image for instant phone camera scanning."""
    target_url = url if url else f"http://{get_local_ip()}:8000/remote"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#141413", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )



@app.get("/api/status")
async def get_system_status():
    """Retrieve real-time system metrics, volume, brightness, battery, and network status."""
    vol_info = get_system_volume()
    brightness = get_system_brightness()
    
    # Battery info via psutil
    battery_info = None
    try:
        bat = psutil.sensors_battery()
        if bat:
            battery_info = {
                "percent": int(bat.percent),
                "power_plugged": bool(bat.power_plugged),
                "secs_left": bat.secsleft if bat.secsleft != psutil.POWER_TIME_UNLIMITED else -1
            }
    except Exception:
        pass

    # CPU & Memory
    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()

    return {
        "status": "online",
        "app_name": "PocketDesk Remote v2.0",
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()} ({platform.architecture()[0]})",
        "local_ip": get_local_ip(),
        "port": 8000,
        "volume": vol_info["volume"],
        "mute": vol_info["mute"],
        "brightness": brightness,
        "cpu_percent": cpu_percent,
        "ram_percent": mem.percent,
        "battery": battery_info,
        "drop_dir": DROP_DIR
    }


# --- Modul A & B: Volume & Brightness ---

@app.get("/api/volume")
async def api_get_volume():
    return get_system_volume()

@app.post("/api/volume")
async def api_set_volume(req: VolumeRequest):
    success = set_system_volume(req.volume)
    return {"success": success, "volume": req.volume}

@app.post("/api/volume/step")
async def api_step_volume(req: VolumeStepRequest):
    cur = get_system_volume()["volume"]
    new_vol = max(0, min(100, cur + req.delta))
    set_system_volume(new_vol)
    return {"success": True, "volume": new_vol}

@app.post("/api/volume/mute")
async def api_toggle_mute(req: MuteRequest):
    new_state = toggle_system_mute(req.mute)
    return {"success": True, "mute": new_state}

@app.get("/api/brightness")
async def api_get_brightness():
    b = get_system_brightness()
    return {"brightness": b}

@app.post("/api/brightness")
async def api_set_brightness(req: BrightnessRequest):
    success = set_system_brightness(req.brightness)
    return {"success": success, "brightness": req.brightness}

@app.post("/api/screen-off")
async def api_screen_off():
    """Turn off laptop display monitor immediately without putting PC to sleep."""
    try:
        # HWND_BROADCAST = 0xFFFF, WM_SYSCOMMAND = 0x0112, SC_MONITORPOWER = 0xF170, 2 = Power OFF
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return {"success": True, "message": "Layar monitor dimatikan. Audio tetap berjalan."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Modul B: YouTube & Media Controls ---

@app.post("/api/youtube/play")
async def api_youtube_play(req: SearchRequest):
    """Direct search on YouTube, extract top video ID without API key, and open in browser."""
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query pencarian tidak boleh kosong")

    video_id = None
    target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "id,en;q=0.9"
    }

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(target_url)
            # Find videoId pattern
            matches = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', resp.text)
            if not matches:
                matches = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', resp.text)
            if matches:
                video_id = matches[0]
                target_url = f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        print(f"[YouTube Search] Query parsing error: {e}")

    launch_browser_url(target_url)
    return {
        "success": True,
        "video_id": video_id,
        "url": target_url,
        "query": query
    }


@app.post("/api/media/playpause")
async def api_media_playpause():
    pyautogui.press('playpause', _pause=False)
    return {"success": True, "action": "playpause"}

@app.post("/api/media/next")
async def api_media_next():
    pyautogui.press('nexttrack', _pause=False)
    return {"success": True, "action": "nexttrack"}

@app.post("/api/media/prev")
async def api_media_prev():
    pyautogui.press('prevtrack', _pause=False)
    return {"success": True, "action": "prevtrack"}

@app.post("/api/media/stop")
async def api_media_stop():
    pyautogui.press('stop', _pause=False)
    return {"success": True, "action": "stop"}


# --- Modul A: Chrome & Quick Search / Wikipedia ---

@app.post("/api/browser/open")
async def api_browser_open():
    launch_browser_url("https://www.google.com")
    return {"success": True, "message": "Browser Chrome dibuka di laptop"}

@app.post("/api/browser/search")
async def api_browser_search(req: SearchRequest):
    q = req.query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query tidak boleh kosong")
    search_url = f"https://www.google.com/search?q={urllib.parse.quote(q)}"
    launch_browser_url(search_url)
    return {"success": True, "query": q, "url": search_url}

@app.post("/api/wiki/summary")
async def api_wiki_summary(req: SearchRequest):
    """Fetch article summary from Wikipedia (ID first, fallback to EN)."""
    q = req.query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query tidak boleh kosong")

    headers = {"User-Agent": "PocketDeskRemote/2.0 (pocketdesk@local.app)"}
    languages = ["id", "en"]

    for lang in languages:
        try:
            search_api = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&utf8=&format=json"
            async with httpx.AsyncClient(timeout=6.0, headers=headers) as client:
                res = await client.get(search_api)
                data = res.json()
                items = data.get("query", {}).get("search", [])
                if not items:
                    continue
                first_title = items[0]["title"]
                
                sum_api = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(first_title)}"
                sum_res = await client.get(sum_api)
                if sum_res.status_code == 200:
                    sum_data = sum_res.json()
                    return {
                        "success": True,
                        "title": sum_data.get("title", first_title),
                        "extract": sum_data.get("extract", "Tidak ada ringkasan teks."),
                        "url": sum_data.get("content_urls", {}).get("desktop", {}).get("page", f"https://{lang}.wikipedia.org/wiki/{first_title}"),
                        "thumbnail": sum_data.get("thumbnail", {}).get("source", ""),
                        "lang": lang.upper()
                    }
        except Exception as e:
            print(f"[Wiki API] Lang {lang} search failed: {e}")
            continue

    return {
        "success": False,
        "message": f"Informasi untuk '{q}' tidak ditemukan di Wikipedia."
    }


# --- Modul C: Touchpad & Mouse Control ---

@app.post("/api/mouse/click")
async def api_mouse_click(req: MouseClickRequest):
    pyautogui.click(button=req.button, _pause=False)
    return {"success": True, "button": req.button}

@app.post("/api/mouse/scroll")
async def api_mouse_scroll(req: MouseScrollRequest):
    amount = req.amount if req.direction == "up" else -req.amount
    pyautogui.scroll(amount, _pause=False)
    return {"success": True, "direction": req.direction}


@app.websocket("/ws/touchpad")
async def websocket_touchpad(websocket: WebSocket):
    """Ultra-low-latency WebSocket endpoint for relative cursor movements, taps, and scrolls."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "move":
                dx = data.get("dx", 0)
                dy = data.get("dy", 0)
                if dx != 0 or dy != 0:
                    pyautogui.moveRel(dx, dy, _pause=False)
                    
            elif msg_type == "click":
                btn = data.get("button", "left")
                pyautogui.click(button=btn, _pause=False)
                
            elif msg_type == "scroll":
                dy = data.get("dy", 0)
                if dy != 0:
                    pyautogui.scroll(int(dy), _pause=False)
                    
            elif msg_type == "down":
                btn = data.get("button", "left")
                pyautogui.mouseDown(button=btn, _pause=False)
                
            elif msg_type == "up":
                btn = data.get("button", "left")
                pyautogui.mouseUp(button=btn, _pause=False)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WebSocket] Touchpad stream disconnected: {e}")


# --- Modul C: Remote Keyboard & Clipboard Sync ---

@app.post("/api/keyboard/type")
async def api_keyboard_type(req: TextRequest):
    """Type text into laptop via clipboard paste for speed & full Unicode/symbol support."""
    text = req.text
    if text:
        # Save previous clipboard, paste text, then restore
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v', _pause=False)
    return {"success": True, "typed": text}

@app.post("/api/keyboard/key")
async def api_keyboard_key(req: KeyRequest):
    k = req.key.lower()
    mapping = {
        "enter": "enter",
        "backspace": "backspace",
        "space": "space",
        "esc": "escape",
        "escape": "escape",
        "tab": "tab",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right"
    }
    actual_key = mapping.get(k, k)
    pyautogui.press(actual_key, _pause=False)
    return {"success": True, "key": actual_key}

@app.post("/api/clipboard/send")
async def api_clipboard_send(req: TextRequest):
    pyperclip.copy(req.text)
    return {"success": True, "length": len(req.text)}

@app.get("/api/clipboard/get")
async def api_clipboard_get():
    try:
        text = pyperclip.paste()
        return {"success": True, "text": text}
    except Exception as e:
        return {"success": False, "text": "", "error": str(e)}


# --- Modul C: Window & Tab Shortcuts ---

@app.post("/api/shortcut")
async def api_shortcut(req: ShortcutRequest):
    sc = req.shortcut.lower()
    if sc == "alt_tab":
        pyautogui.hotkey('alt', 'tab', _pause=False)
    elif sc == "ctrl_w":
        pyautogui.hotkey('ctrl', 'w', _pause=False)
    elif sc == "f11":
        pyautogui.press('f11', _pause=False)
    elif sc == "win_d":
        pyautogui.hotkey('win', 'd', _pause=False)
    elif sc == "space":
        pyautogui.press('space', _pause=False)
    else:
        raise HTTPException(status_code=400, detail="Shortcut tidak dikenal")
    return {"success": True, "shortcut": sc}


# --- Modul D: Quick File Drop & Open Folder ---

@app.post("/api/upload")
async def api_upload_files(files: List[UploadFile] = File(...)):
    """Accept single or multiple file uploads and save to ~/Downloads/PocketDesk_Drop."""
    saved_files = []
    total_bytes = 0

    for file in files:
        # Sanitize filename
        clean_name = os.path.basename(file.filename)
        dest_path = os.path.join(DROP_DIR, clean_name)
        
        # Avoid accidental overwrite by suffixing number if exists
        base, ext = os.path.splitext(clean_name)
        counter = 1
        while os.path.exists(dest_path):
            clean_name = f"{base}_{counter}{ext}"
            dest_path = os.path.join(DROP_DIR, clean_name)
            counter += 1

        content = await file.read()
        total_bytes += len(content)
        with open(dest_path, "wb") as f_out:
            f_out.write(content)

        saved_files.append({
            "name": clean_name,
            "size": len(content),
            "path": dest_path
        })

    return {
        "success": True,
        "count": len(saved_files),
        "total_bytes": total_bytes,
        "saved_files": saved_files,
        "drop_dir": DROP_DIR
    }


@app.post("/api/files/open-folder")
async def api_open_drop_folder():
    """Open the PocketDesk Drop folder in Windows Explorer."""
    try:
        os.startfile(DROP_DIR)
        return {"success": True, "path": DROP_DIR}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Modul D: Live Peek Screen (Screenshot & Live Stream) ---

def get_screen_jpeg(max_width: int = 960, quality: int = 60) -> bytes:
    """Fast screen capture resized and encoded to JPEG for mobile streaming."""
    try:
        img = capture_screenshot()
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=False)
        return buf.getvalue()
    except Exception as e:
        print(f"[Screen Capture] Error: {e}")
        buf = io.BytesIO()
        Image.new("RGB", (640, 360), (15, 23, 42)).save(buf, format="JPEG")
        return buf.getvalue()


@app.get("/api/screen/peek")
async def api_screen_peek():
    """Capture laptop screen and return single JPEG image optimized for mobile viewing."""
    try:
        jpeg_data = get_screen_jpeg(max_width=1280, quality=75)
        return Response(content=jpeg_data, media_type="image/jpeg", headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/screen/stream")
async def api_screen_stream(fps: int = 8, quality: int = 60, width: int = 960):
    """Real-time continuous MJPEG live stream of laptop desktop for live screening."""
    fps = max(1, min(20, fps))
    interval = 1.0 / fps

    async def stream_frames():
        loop = asyncio.get_event_loop()
        try:
            while True:
                start_time = time.time()
                frame_data = await loop.run_in_executor(None, get_screen_jpeg, width, quality)
                header = (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame_data)).encode() + b"\r\n\r\n"
                )
                yield header + frame_data + b"\r\n"
                elapsed = time.time() - start_time
                sleep_dur = max(0.01, interval - elapsed)
                await asyncio.sleep(sleep_dur)
        except (asyncio.CancelledError, GeneratorExit):
            pass
        except Exception:
            pass

    return StreamingResponse(
        stream_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "close"
        }
    )


@app.post("/api/screen/click")
async def api_screen_click(req: ScreenClickRequest):
    """Directly click at normalized (0.0 to 1.0) coordinates on the laptop screen."""
    try:
        sw, sh = pyautogui.size()
        cx = int(max(0.0, min(1.0, req.x)) * (sw - 1))
        cy = int(max(0.0, min(1.0, req.y)) * (sh - 1))
        btn = "right" if req.button == "right" else "left"
        clicks = max(1, min(3, req.clicks))
        pyautogui.click(x=cx, y=cy, button=btn, clicks=clicks, _pause=False)
        return {"success": True, "x": cx, "y": cy, "button": btn, "clicks": clicks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/screen/move")
async def api_screen_move(req: ScreenClickRequest):
    """Move cursor to normalized (0.0 to 1.0) coordinates on laptop screen."""
    try:
        sw, sh = pyautogui.size()
        cx = int(max(0.0, min(1.0, req.x)) * (sw - 1))
        cy = int(max(0.0, min(1.0, req.y)) * (sh - 1))
        pyautogui.moveTo(x=cx, y=cy, _pause=False)
        return {"success": True, "x": cx, "y": cy}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Modul D: Notifications & TTS ---

@app.post("/api/notify/popup")
async def api_notify_popup(req: MessageRequest):
    """Show non-blocking Win32 MessageBox on top of all windows."""
    msg = req.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong")

    def show_box():
        # MB_OK (0x0) | MB_ICONINFORMATION (0x40) | MB_SYSTEMMODAL (0x1000) = 0x1040
        ctypes.windll.user32.MessageBoxW(0, msg, "Pesan dari PocketDesk Remote", 0x00001040)

    threading.Thread(target=show_box, daemon=True).start()
    return {"success": True, "message": "Pop-up ditampilkan di laptop"}


@app.post("/api/notify/tts")
async def api_notify_tts(req: MessageRequest):
    """Speak text aloud using laptop speakers via pyttsx3."""
    msg = req.message.strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong")

    threading.Thread(target=speak_worker, args=(msg,), daemon=True).start()
    return {"success": True, "message": "Pesan sedang dibacakan di speaker laptop"}


# --- Modul E: Power & System Controls ---

@app.post("/api/power/lock")
async def api_power_lock():
    """Lock the Windows workstation immediately."""
    ctypes.windll.user32.LockWorkStation()
    return {"success": True, "action": "lock"}

@app.post("/api/power/sleep")
async def api_power_sleep():
    """Put laptop to sleep."""
    subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=True)
    return {"success": True, "action": "sleep"}

@app.post("/api/power/shutdown")
async def api_power_shutdown():
    """Initiate Windows shutdown with 15-second grace countdown timer."""
    subprocess.Popen(["shutdown", "/s", "/t", "15"], shell=True)
    return {"success": True, "action": "shutdown", "countdown": 15}

@app.post("/api/power/cancel-shutdown")
async def api_power_cancel_shutdown():
    """Cancel any pending shutdown."""
    subprocess.Popen(["shutdown", "/a"], shell=True)
    return {"success": True, "action": "cancel_shutdown"}


# ---------------------------------------------------------------------------
# JARVIS AI Voice & Chat Integration Endpoints
# ---------------------------------------------------------------------------

JARVIS_GATEWAY_URL = "http://127.0.0.1:8765"
JARVIS_DIR = r"D:\JARVIS"


@app.get("/api/jarvis/status")
async def api_jarvis_status():
    """Check JARVIS IPC gateway status."""
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{JARVIS_GATEWAY_URL}/api/status")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "online": True,
                    "model": data.get("model", "qwen3:8b"),
                    "language": data.get("language", "id"),
                    "version": data.get("version", "2.5")
                }
    except Exception:
        pass
    return {"online": False, "model": None, "language": "id", "version": None}


@app.post("/api/jarvis/start")
async def api_jarvis_start():
    """Launch JARVIS on the laptop if it is not currently running."""
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            resp = await client.get(f"{JARVIS_GATEWAY_URL}/api/status")
            if resp.status_code == 200:
                return {"success": True, "message": "JARVIS is already running"}
    except Exception:
        pass

    bat_path = os.path.join(JARVIS_DIR, "run_gui.bat")
    if not os.path.exists(bat_path):
        return {"success": False, "error": f"Launcher not found at {bat_path}"}

    try:
        flags = subprocess.CREATE_NEW_CONSOLE if platform.system() == "Windows" else 0
        subprocess.Popen(["cmd.exe", "/c", bat_path], cwd=JARVIS_DIR, creationflags=flags)
        return {"success": True, "message": "JARVIS is starting..."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@app.post("/api/jarvis/message")
async def api_jarvis_message(req: JarvisMessageRequest):
    """Relay text command to JARVIS Gateway."""
    cmd_text = req.text.strip()
    if not cmd_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{JARVIS_GATEWAY_URL}/api/process",
                json={"text": cmd_text, "audio_target": req.audio_target or "laptop"}
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                return JSONResponse(status_code=resp.status_code, content=resp.json())
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="JARVIS is offline. Start JARVIS first.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/jarvis/voice")
async def api_jarvis_voice(audio: UploadFile = File(...), audio_target: str = Form("laptop")):
    """Upload voice recording from phone, transcribe using JARVIS Whisper, and process command."""
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio recording")

    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            # 1. Transcribe via JARVIS Gateway
            transcribe_resp = await client.post(
                f"{JARVIS_GATEWAY_URL}/api/transcribe",
                content=audio_bytes,
                headers={"Content-Type": "audio/wav"}
            )
            if transcribe_resp.status_code != 200:
                detail = transcribe_resp.json().get("error", "Transcription failed")
                raise HTTPException(status_code=transcribe_resp.status_code, detail=detail)

            transcription = transcribe_resp.json().get("transcription", "").strip()
            if not transcription:
                return {
                    "success": False,
                    "transcription": "",
                    "reply": "Suara tidak terdengar jelas atau terlalu hening, sir.",
                    "audio_base64": ""
                }

            # 2. Process command
            process_resp = await client.post(
                f"{JARVIS_GATEWAY_URL}/api/process",
                json={"text": transcription, "audio_target": audio_target}
            )
            data = process_resp.json()
            data["transcription"] = transcription
            return data
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="JARVIS is offline. Start JARVIS first.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Server Startup Banner & QR Code
# ---------------------------------------------------------------------------

def print_banner(ip: str, port: int):
    landing_url = f"http://{ip}:{port}"
    remote_url = f"http://{ip}:{port}/remote"
    banner = f"""
======================================================================
  POCKETDESK REMOTE v2.0 - LOCAL DESKTOP AUTOMATION SERVER
======================================================================
  Server aktif di jaringan lokal Wi-Fi!
  
  🌐 Landing Page (Info & Input IP):
  👉  \033[1;36m{landing_url}\033[0m
  
  📱 Remote Controller Langsung:
  👉  \033[1;32m{remote_url}\033[0m
  (Atau akses dari laptop ini: http://localhost:{port})

  Folder File Drop: {DROP_DIR}
----------------------------------------------------------------------
  Pindai (Scan) QR Code berikut dari kamera smartphone Anda:
"""
    print(banner)
    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(remote_url)
        qr.print_ascii(invert=True)
    except Exception as e:
        print(f"  [Info] QR Code rendering: {remote_url} ({e})")
    print("======================================================================\n")



if __name__ == "__main__":
    import uvicorn
    local_ip = get_local_ip()
    port = 8000
    print_banner(local_ip, port)
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
