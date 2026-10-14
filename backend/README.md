# ⚙️ Backend — Sistem Booking Ruangan (JSON-RPC 2.0 Service)

Layanan backend sistem reservasi ruangan berbasis **Sistem Terdistribusi** yang mengimplementasikan protokol **JSON-RPC 2.0**.

Sistem ini memiliki dua cara eksekusi:
1. **Django Core & Admin (Port 8000)**: Mengelola database ORM, migrasi skema, panel admin modern (Django Unfold), dan native RPC endpoint `/api/rpc/`.
2. **Flask Standalone RPC Server (Port 5000)** — `rpc_server.py`: Microservice RPC independen yang langsung terhubung ke database ORM Django untuk kebutuhan tugas Sistem Terdistribusi.

---

## 🛠️ Tech Stack
- **Bahasa**: Python 3.11 / 3.12+
- **Core Framework**: Django 5.0, Django REST Framework
- **RPC Microservice**: Flask 3.0, Flask-CORS
- **Admin Theme**: Django Unfold
- **Database**: SQLite (`db.sqlite3`) / PostgreSQL
- **Media**: Pillow untuk handling gambar/upload bukti transfer

---

## ⚙️ Konfigurasi Environment (`.env`)

Salin file `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```

Isi konfigurasi pada file `.env`:
```env
SECRET_KEY=ganti-dengan-secret-key-rahasia-anda
DEBUG=True
ALLOWED_HOSTS=*
DATABASE_URL=sqlite:///db.sqlite3
PORT=5000
```

---

## 🚀 Cara Menjalankan (Development)

1. Masuk ke direktori `backend`:
   ```bash
   cd backend
   ```

2. Buat & aktifkan Virtual Environment:
   * **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate
     ```
   * **Linux / macOS:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```

4. Jalankan migrasi database:
   ```bash
   python manage.py migrate
   ```

5. *(Opsional)* Isi data awal ruangan & akun pengujian:
   ```bash
   python seed_rooms.py
   ```

6. Jalankan Server:
   * **Opsi A: Django Server (Direkomendasikan untuk Admin & RPC)**
     ```bash
     python manage.py runserver 0.0.0.0:8000
     ```
     - Endpoint RPC: `http://localhost:8000/api/rpc/`
     - Admin Panel: `http://localhost:8000/admin/`
   * **Opsi B: Flask RPC Microservice (Port 5000)**
     ```bash
     python rpc_server.py
     ```
     - Endpoint RPC: `http://localhost:5000/api/rpc/`

---

## 👤 Akun Bawaan (Default Accounts)

| Role | Username / Email | Password | Kegunaan |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | Login Panel Django Admin (`/admin`) |
| **User** | `rania@gmail.com` | `rania123` | Testing reservasi di Frontend |

---

## 🐳 Deployment Home Server dengan Docker

Backend dapat dibuild dan dijalankan langsung menggunakan Docker:
```bash
# Dari root directory
docker compose up --build -d backend
```
Data `db.sqlite3` dan `media/` dipetakan ke host volume agar data reservasi dan upload bukti bayar tidak terhapus saat container di-restart.
