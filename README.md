# 🏠 Sistem Reservasi Ruangan (Distributed System — JSON-RPC 2.0)

Aplikasi Reservasi Ruangan Full-Stack berbasis **Arsitektur Sistem Terdistribusi** menggunakan protokol komunikasi **JSON-RPC 2.0 (Remote Procedure Call)**.

Aplikasi ini dibangun untuk memenuhi spesifikasi praktikum Sistem Terdistribusi, di mana komunikasi antara antarmuka pengguna (Frontend) dan layanan backend sepenuhnya menggunakan protokol pemanggilan prosedur jarak jauh (*remote procedure call*) melalui endpoint tunggal `/api/rpc/`.

---

## 🏗️ Arsitektur Sistem Terdistribusi

```text
       ┌─────────────────────────────────────────────────────────┐
       │               Frontend Client (React 18 + Vite)         │
       │                   Port: 5173 (Dev) / 3000 (Docker)      │
       └────────────────────────────┬────────────────────────────┘
                                    │
                                    │ JSON-RPC 2.0 (HTTP POST)
                                    │ Payload: { "jsonrpc": "2.0", "method": "...", "params": {...}, "id": 1 }
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │                   Endpoint: /api/rpc/                   │
       └────────────────────────────┬────────────────────────────┘
                                    │
             ┌──────────────────────┴──────────────────────┐
             ▼                                             ▼
   [ Flask RPC Microservice ]                     [ Django RPC Service ]
          (Port: 5000)                                  (Port: 8000)
    Layanan RPC Standalone                         Layanan RPC Native & Admin
             │                                             │
             └──────────────────────┬──────────────────────┘
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────┐
       │            Django ORM & SQLite (db.sqlite3)             │
       │    Ruangan, Reservasi, User, Pembayaran, Review, Notif  │
       └─────────────────────────────────────────────────────────┘
```

---

## 🔒 File yang TIDAK BOLEH Di-Push ke Git

Seluruh aturan ini telah dikonfigurasi secara aman di dalam file [`.gitignore`](file:///.gitignore):

| File / Folder | Alasan TIDAK Boleh Di-Push | Solusi Aman |
| :--- | :--- | :--- |
| **`backend/.env` & `frontend/.env`** | Berisi rahasia kredensial (`SECRET_KEY`, konfigurasi server). | Hanya push file template `.env.example`. |
| **`db.sqlite3`** | Berisi data database transaksi lokal. Jika ter-push, akan **menimpa data di Home Server** saat melakukan `git pull`. | Biarkan database terbentuk di Home Server via migrasi. |
| **`media/` & `backend/media/`** | Berisi file upload lokal (foto profil user, bukti transfer). | Disimpan di storage lokal masing-masing server. |
| **`venv/` / `.venv/`** | Folder *virtual environment* Python (ukuran ratusan MB & terikat OS lokal). | Install ulang di server via `pip install -r requirements.txt`. |
| **`node_modules/`** | Dependensi pustaka Node.js (ukuran sangat besar). | Install ulang di server via `npm install`. |
| **`dist/`** | File hasil kompilasi frontend lokal. | Dihasilkan otomatis saat `npm run build` atau proses build Docker. |

---

## 🚀 Cara Menjalankan Secara Lokal (Development)

### 1. Backend

Buka Terminal 1:
```powershell
# 1. Masuk ke direktori backend
cd backend

# 2. Aktifkan Virtual Environment
.\venv\Scripts\Activate
# (Jika di Linux/macOS: source venv/bin/activate)

# 3. Pastikan dependensi terpasang
pip install -r requirements.txt

# 4. Jalankan migrasi database
python manage.py migrate

# 5. Jalankan server (Pilih salah satu):
# Opsi A: Django Server (Port 8000 — Disarankan: Mendukung Admin & RPC)
python manage.py runserver 0.0.0.0:8000

# Opsi B: Standalone Flask RPC Server (Port 5000)
python rpc_server.py
```
* **Endpoint JSON-RPC:** `http://localhost:8000/api/rpc/` (atau `http://localhost:5000/api/rpc/`)
* **Panel Admin Django:** `http://localhost:8000/admin/`

---

### 2. Frontend

Buka Terminal 2:
```bash
# 1. Masuk ke direktori frontend
cd frontend

# 2. Pasang dependensi
npm install

# 3. Jalankan Vite dev server
npm run dev
```
* **Akses Website Client:** `http://localhost:5173`

---

## 👤 Akun Bawaan untuk Pengujian (Default Credentials)

| Akun | Username / Email | Password | Hak Akses & Fungsi |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `admin` | `admin123` | Akses penuh ke Django Unfold Admin Panel |
| **User Biasa** | `rania@gmail.com` | `rania123` | Booking ruangan, riwayat sewa, dan notifikasi |

---

## 🏠 Panduan Deployment di Home Server (Ubuntu / Linux)

Menghosting di Home Server sangat disarankan menggunakan **Docker Compose**, karena seluruh lingkungan server terisolasi, otomatis restart jika mati lampu, dan data database tetap aman (*persistent*).

### Langkah 1: Clone Repository ke Home Server
```bash
git clone <URL_REPOSITORY_ANDA>
cd room-books
```

### Langkah 2: Siapkan File Environment
Salin template `.env.example` ke `.env`:
```bash
# Backend
cp backend/.env.example backend/.env

# Frontend
cp frontend/.env.example frontend/.env
```
*Edit file `backend/.env` di server dan ubah `SECRET_KEY` dengan string acak yang aman.*

### Langkah 3: Jalankan Service dengan Docker Compose
```bash
docker compose up --build -d
```
Docker Compose akan otomatis:
1. Mem-build image backend (Python) & frontend (Nginx + React).
2. Memetakan volume `./backend/db.sqlite3` dan `./backend/media` ke disk Home Server Anda (sehingga database transaksi dan foto bukti bayar **tidak akan hilang** saat container di-restart atau di-update).
3. Menjalankan service di background (*daemon mode*) dengan kebijakan *restart: unless-stopped*.

### Langkah 4: Cek Status Container
```bash
docker compose ps
```
Aplikasi kini berjalan di Home Server:
* **Frontend Web:** `http://<IP_HOME_SERVER>:3000`
* **Backend RPC:** `http://<IP_HOME_SERVER>:5000/api/rpc/`

### Langkah 5: Cara Update Aplikasi di Home Server
Setiap kali ada pembaruan kode dari Git:
```bash
git pull origin main
docker compose up --build -d
```
*(Data database `db.sqlite3` dan folder `media/` tetap utuh dan aman).*

---

### 🌐 Opsi Akses dari Luar Rumah (Public Domain)

Agar aplikasi di Home Server dapat diakses dari internet tanpa perlu IP Publik Statis atau Port Forwarding di router:
1. **Cloudflare Tunnel (Sangat Disarankan)**:
   * Pasang `cloudflared` di Home Server.
   * Hubungkan domain Anda ke service `http://localhost:3000`.
   * Anda mendapatkan HTTPS/SSL gratis dan aman tanpa membuka port router.
2. **Tailscale / WireGuard**:
   * Cocok jika akses hanya untuk Anda sendiri atau kelompok internal.

---

## 📡 Daftar Prosedur JSON-RPC 2.0 (Method Registry)

Seluruh request client dikirim dengan format:
```json
{
  "jsonrpc": "2.0",
  "method": "<nama_method>",
  "params": { ... },
  "id": 1
}
```

| Modul | Method Name | Deskripsi Prosedur |
| :--- | :--- | :--- |
| **Autentikasi** | `auth.login` | Autentikasi user & penerbitan token JWT |
| | `auth.register` | Registrasi akun baru |
| | `auth.get_profile` | Mengambil data profil user aktif |
| | `auth.update_profile` | Memperbarui nama, telepon, dan foto profil |
| | `auth.change_password` | Mengganti kata sandi akun |
| **Ruangan** | `room.get_list` | Mengambil daftar ruangan dengan filter kapasitas/harga |
| | `room.get_detail` | Mengambil informasi detail ruangan |
| | `room.get_amenities` | Mengambil daftar fasilitas ruangan |
| | `room.check_availability` | Cek ketersediaan jadwal (mendukung lewat tengah malam & 24 jam) |
| **Reservasi** | `booking.create` | Membuat reservasi ruangan baru |
| | `booking.get_my_bookings`| Mengambil riwayat booking pengguna |
| | `booking.get_detail` | Mengambil rincian pemesanan tertentu |
| | `booking.cancel` | Membatalkan pemesanan |
| **Pembayaran** | `payment.submit` | Upload bukti transfer pembayaran |
| | `invoice.get_detail` | Mengambil data invoice dan kalkulasi pajak 11% |
| **Review** | `review.get_list` | Mengambil ulasan ruangan |
| | `review.create` | Menambahkan ulasan dan rating ruangan |
| **Notifikasi** | `notification.get_unread_count` | Jumlah notifikasi belum dibaca |
| | `notification.get_list` | Mengambil daftar notifikasi pengguna |
| | `notification.mark_as_read` | Menandai satu notifikasi telah dibaca |
| | `notification.mark_all_as_read` | Menandai semua notifikasi telah dibaca |

---

## 📂 Struktur Direktori Proyek

```text
room-books/
├── .gitignore              # Konfigurasi file yang diabaikan Git
├── docker-compose.yml      # Konfigurasi multi-container Home Server
├── README.md               # Dokumentasi utama proyek
├── backend/                # Layanan Backend (Django & Flask)
│   ├── .env.example        # Template konfigurasi environment backend
│   ├── Dockerfile          # Image container backend
│   ├── rpc_server.py       # Standalone Flask JSON-RPC Server (Port 5000)
│   ├── manage.py           # CLI Django
│   ├── config/             # Pengaturan Django (settings, urls, wsgi)
│   └── core/               # Aplikasi utama (models, rpc_dispatcher, views)
└── frontend/               # Layanan Frontend (React + Vite)
    ├── .env.example        # Template konfigurasi environment frontend
    ├── Dockerfile          # Image container frontend (Nginx multi-stage)
    ├── nginx.conf          # Konfigurasi Nginx & reverse proxy /api/
    ├── package.json        # Dependensi pustaka frontend
    ├── README.md           # Dokumentasi khusus frontend
    └── src/                # Kode sumber React (pages, components, utils)
```
