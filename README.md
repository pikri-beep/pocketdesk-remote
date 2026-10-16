# 📱 PocketDesk Remote (v2.0)

**PocketDesk Remote** adalah aplikasi kendali jarak jauh (*all-in-one desktop remote control*) berbasis jaringan lokal (Wi-Fi/LAN) untuk mengontrol laptop/PC Windows langsung dari *browser smartphone* tanpa perlu menginstal aplikasi tambahan di HP.

Dirancang dengan antarmuka **Tactile Hardware Remote** modern (*Zero-Scroll 100dvh*) layaknya remot Apple TV / Google TV.

---

## ✨ Fitur Utama

- 🖱️ **Virtual Touchpad & D-Pad:** Area sentuh navigasi kursor halus, *tap* klik kiri, *2-finger scroll*, tombol fisik klik kiri & kanan, serta mode *D-Pad Directional Keys* (Atas, Bawah, Kiri, Kanan, OK).
- 🔊 **Vertical Volume Rocker:** Pengatur volume sistem Windows real-time (Vol +, Vol -, Mute, dan persentase level).
- ☀️ **Vertical Brightness Rocker:** Pengatur kecerahan monitor laptop (Bright +, Bright -, dan persentase level).
- 📺 **Media Deck & Buka Chrome:** Kontrol media (*Play/Pause*, *Next*, *Prev*) dan tombol cepat membuka Google Chrome.
- 🪟 **Window Quick-Keys:** Pintasan satu tombol untuk `Alt+Tab` (Ganti App), `F11` (Fullscreen), `Ctrl+W` (Tutup Tab), dan `Win+D` (Desktop).
- 💤 **Screen Off & Manajemen Daya:**
  - **Screen Off:** Mematikan monitor laptop seketika tanpa *sleep* (musik tetap menyala).
  - **Power Menu:** *Lock Screen*, *Sleep*, *Shutdown (15s grace period)*, dan *Batalkan Shutdown*.
- 🔍 **Smart Play & Search:** Pencarian dan pemutaran otomatis video YouTube teratas, Google Search ke laptop, dan ringkasan artikel Wikipedia langsung di HP.
- ⌨️ **Remote Keyboard & Clipboard Sync:** Mengetik teks jarak jauh, tombol `Enter`/`Backspace`/`Esc`, serta kirim/ambil teks clipboard antara HP dan laptop.
- 👁️ **Live Screen Peek:** Tangkapan layar (*screenshot*) desktop laptop secara real-time untuk memantau aktivitas.
- 📁 **Quick File Drop:** Mengunggah file dari smartphone langsung ke folder `Downloads/PocketDesk_Drop` di laptop dilengkapi *progress bar*.
- 📢 **Pop-up Alert & Text-to-Speech (TTS):** Menampilkan notifikasi *pop-up* di layar laptop atau membacakan pesan suara via speaker laptop.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, FastAPI, Uvicorn, WebSockets.
- **Automasi Windows:** `pyautogui`, `pycaw`, `screen-brightness-control`, `pyperclip`, `pyttsx3`, `mss`, `Pillow`, Win32 API (`ctypes`).
- **Frontend:** Single Page Application (SPA), HTML5, Vanilla JavaScript, Tailwind CSS (CDN), Lucide Icons.

---

## 🚀 Cara Menjalankan

### 1. Prasyarat
- Pastikan Python 3.10 atau versi lebih baru telah terinstal di Windows dan terdaftar di PATH.
- Smartphone dan laptop harus terhubung dalam **jaringan Wi-Fi / hotspot yang sama**.

### 2. Instalasi & Menjalankan Server
Cukup klik ganda (double-click) file:
```cmd
start_remote.bat
```
Atau jalankan secara manual melalui terminal:
```bash
pip install -r requirements.txt
python main.py
```

### 3. Menghubungkan Smartphone
- Terminal laptop akan menampilkan banner IP dan **QR Code**.
- Pindai (scan) QR Code menggunakan kamera smartphone Anda atau buka URL yang tertera (misal: `http://192.168.x.x:8000/remote`).
- Anda juga dapat membuka `http://192.168.x.x:8000/` untuk mengakses *landing page*.

---

## 📄 Lisensi
Proyek ini dilisensikan di bawah lisensi [MIT](LICENSE).
