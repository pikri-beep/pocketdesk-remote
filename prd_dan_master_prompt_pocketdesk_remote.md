# Product Requirements Document (PRD): PocketDesk Remote (v2.0)

## 1. Ringkasan Proyek (Project Overview)
**PocketDesk Remote** adalah aplikasi kendali jarak jauh (*all-in-one remote control*) berbasis jaringan lokal (Wi-Fi/LAN) untuk mengontrol laptop/PC Windows langsung dari *browser smartphone*. Sistem ini menggabungkan fungsi peluncur aplikasi, pengendali media, *virtual touchpad & keyboard*, kontrol visual layar, hingga transfer file instan dalam satu antarmuka web *mobile-first* yang ergonomis tanpa perlu menginstal aplikasi tambahan di HP.

---

## 2. Tujuan & Sasaran (Objectives)
* **Kontrol Penuh Tanpa Beranjak:** Mengakomodasi kebutuhan navigasi penuh (kursor, ketikan, pindah jendela) dan kontrol media dari jarak jauh (misalnya dari tempat tidur atau sofa).
* **Kenyamanan Visual & Audio:** Memungkinkan pengaturan kecerahan layar, volume, hingga mematikan lampu monitor tanpa menghentikan musik yang sedang diputar.
* **Produktivitas Lintas Perangkat:** Mempermudah pengiriman file dari HP ke laptop, sinkronisasi teks *clipboard*, pencarian informasi cepat, serta pengiriman pengingat/notifikasi suara ke laptop.
* **Latensi Rendah & Antarmuka Rapi:** Menggunakan kombinasi REST API dan WebSocket (khusus *touchpad*) dengan tata letak berbasis *Tab Navigasi Bawah* (*Bottom Navigation Bar*) agar layar HP tetap rapi dan nyaman dioperasikan satu tangan.

---

## 3. Spesifikasi Fungsional (Functional Requirements)

### Modul A: Peluncur Cepat, Web & Informasi
| Kode | Fitur | Deskripsi Fungsional | Implementasi Teknis (Sisi Laptop) |
| :--- | :--- | :--- | :--- |
| **FR-01** | **Buka Chrome & URL** | Tombol instan untuk membuka Google Chrome atau membuka situs favorit di tab baru. | Modul `subprocess` / `webbrowser` memanggil *executable* Chrome. |
| **FR-02** | **Google Search ke Laptop** | Kolom *input* di HP untuk mengetik kueri pencarian dan langsung membuka hasilnya di Chrome laptop. | Encode kueri ke `https://www.google.com/search?q=...` lalu buka di browser laptop. |
| **FR-03** | **Pencarian Informasi Cepat (Quick Info)** | Mencari ringkasan informasi/definisi yang hasilnya langsung tampil di layar HP, dilengkapi tombol *"Buka di Laptop"*. | Fetch API Wikipedia (ID/EN) atau DuckDuckGo Instant Answer API via `httpx`. |

### Modul B: Media, Audio & Kenyamanan Visual
| Kode | Fitur | Deskripsi Fungsional | Implementasi Teknis (Sisi Laptop) |
| :--- | :--- | :--- | :--- |
| **FR-04** | **Pemutar Musik YouTube** | Mengetik judul lagu di HP, lalu laptop otomatis membuka dan langsung memutar video hasil teratas di YouTube, dilengkapi tombol *Play/Pause*, *Next*, dan *Prev*. | Ekstraksi *Video ID* pertama dari pencarian YouTube + buka URL `watch?v=<ID>` + `pyautogui` untuk *media keys*. |
| **FR-05** | **Kontrol Volume Sistem** | *Slider* volume (0–100%), tombol *Mute/Unmute*, serta tombol *Vol +10%* dan *Vol -10%*. | Library `pycaw` & `comtypes` untuk membaca dan mengubah *Master Volume* Windows. |
| **FR-06** | **Kontrol Kecerahan (Brightness)** | *Slider* (0–100%) untuk meredupkan atau menerangkan layar laptop dari HP. | Library `screen-brightness-control` (`sbc.set_brightness()`). |
| **FR-07** | **Matikan Layar Saja (Screen Off)** | Mematikan lampu monitor laptop sepenuhnya tanpa membuat laptop *sleep* agar musik YouTube tetap menyala. | Win32 API via `ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)`. |
| **FR-08** | **Intip Layar (Live Peek Screen)** | Mengambil *screenshot* layar laptop saat itu juga dan menampilkannya di layar HP (bisa di-*zoom*). | Library `mss` atau `Pillow` (`ImageGrab`), dikonversi ke JPEG/Base64 dan dikirim ke UI HP. |

### Modul C: Navigasi, Virtual Touchpad & Input
| Kode | Fitur | Deskripsi Fungsional | Implementasi Teknis (Sisi Laptop) |
| :--- | :--- | :--- | :--- |
| **FR-09** | **Virtual Touchpad & Klik** | Area sentuh (*touchpad*) di HP untuk menggerakkan kursor mouse laptop secara mulus, disertai tombol Klik Kiri, Klik Kanan, dan *Scroll* Atas/Bawah. | WebSocket endpoint (`/ws/touchpad`) yang meneruskan koordinat $\Delta x$ dan $\Delta y$ ke `pyautogui.moveRel()` & `pyautogui.scroll()`. |
| **FR-10** | **Remote Keyboard & Clipboard Sync** | Kolom untuk mengetik teks di HP agar langsung terketik di laptop (termasuk tombol `Enter` & `Backspace`), serta fitur kirim/ambil teks *Clipboard* antara HP dan laptop. | `pyperclip.copy()` + `pyautogui.hotkey('ctrl', 'v')` (mendukung karakter unik/emoji dengan cepat). |
| **FR-11** | **Navigasi Jendela & Tab** | Tombol pintasan cepat: `Alt + Tab` (Pindah Aplikasi), `Ctrl + W` (Tutup Tab Chrome), `F11` (Fullscreen), dan `Win + D` (Tampilkan Desktop/Minimize All). | Eksekusi kombinasi tombol melalui `pyautogui.hotkey()` dan `pyautogui.press()`. |

### Modul D: Produktivitas & Transfer Cepat
| Kode | Fitur | Deskripsi Fungsional | Implementasi Teknis (Sisi Laptop) |
| :--- | :--- | :--- | :--- |
| **FR-12** | **Quick File Drop** | Mengunggah (*upload*) satu atau beberapa file (foto, dokumen, APK, dll.) dari HP yang langsung tersimpan di folder `Downloads/PocketDesk_Drop` di laptop. | Endpoint `POST /api/upload` menggunakan `UploadFile` (`python-multipart`) dengan indikator *progress bar* di HP. |
| **FR-13** | **Notifikasi Pop-up & Text-to-Speech (TTS)** | Mengetik pesan di HP dengan pilihan: tampilkan sebagai *Pop-up Alert* di tengah layar laptop, dan/atau bacakan keras-keras menggunakan suara sistem laptop (TTS). | Thread terpisah menjalankan `ctypes.windll.user32.MessageBoxW` untuk *pop-up* dan `pyttsx3` untuk suara *Text-to-Speech*. |

### Modul E: Manajemen Daya (Power Control)
| Kode | Fitur | Deskripsi Fungsional | Implementasi Teknis (Sisi Laptop) |
| :--- | :--- | :--- | :--- |
| **FR-14** | **Manajemen Daya & Keamanan** | Tombol untuk **Sleep**, **Lock Screen**, **Shutdown (Timer 15 detik)**, dan **Batalkan Shutdown**, dilengkapi *modal* konfirmasi agar tidak terpencet secara tidak sengaja. | Perintah OS Windows (`shutdown /s /t 15`, `shutdown /a`, `rundll32.exe user32.dll,LockWorkStation`, dll.). |

---

## 4. Arsitektur & Tech Stack
* **Backend Server:** Python 3.10+ dengan **FastAPI** & **Uvicorn** (mendukung REST API untuk perintah tombol/upload dan WebSocket untuk pergerakan *touchpad* *real-time*).
* **Library Otomasi Windows:**
  * Audio: `pycaw`, `comtypes`
  * Layar & Visual: `screen-brightness-control`, `mss` / `Pillow`, `ctypes` (Win32 API)
  * Input & Jendela: `pyautogui`, `pyperclip`
  * Suara & Jaringan: `pyttsx3`, `httpx`, `qrcode`, `python-multipart`
* **Frontend (Mobile Web UI):** Single-Page Application (`static/index.html`) menggunakan **HTML5, Tailwind CSS (CDN), Lucide Icons, dan Vanilla JavaScript**.
* **Struktur Navigasi UI HP (4 Tab Bawah):**
  1. **Tab Media & Web:** Volume, Brightness, Screen Off, YouTube Player, Google Search, Quick Info.
  2. **Tab Touchpad & Input:** Area Virtual Touchpad, Klik Kiri/Kanan/Scroll, Pintasan Jendela (`Alt+Tab`, `F11`, `Ctrl+W`, `Win+D`), Remote Keyboard & Clipboard.
  3. **Tab Tools & File:** Quick File Drop (Upload File), Live Peek Screen (Screenshot), Kirim Notifikasi Pop-up / Text-to-Speech.
  4. **Tab Power:** Lock Screen, Sleep, Shutdown, Cancel Shutdown.

---
---


