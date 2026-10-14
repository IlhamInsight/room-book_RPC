# 💻 Frontend — Sistem Booking Ruangan (Client Web)

Aplikasi antarmuka web client untuk sistem reservasi ruangan berbasis **React 18**, **Vite**, dan **Tailwind CSS**, yang berkomunikasi sepenuhnya dengan backend melalui protokol **JSON-RPC 2.0**.

---

## 🛠️ Tech Stack
- **Framework & Tooling**: [React 18](https://react.dev/), [Vite](https://vitejs.dev/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Animation**: [Framer Motion](https://www.framer.com/motion/)
- **State Management**: [Zustand](https://zustand-demo.pmnd.rs/)
- **Komunikasi Data**: Native JSON-RPC 2.0 Client (`src/utils/rpcClient.js`)

---

## ⚙️ Konfigurasi Environment (`.env`)

Salin file `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```

Isi konfigurasi pada file `.env`:
```env
# Mode Development (koneksi langsung ke server lokal):
VITE_API_URL=http://localhost:8000/api
VITE_RPC_URL=http://localhost:8000/api/rpc/
VITE_DEBUG=true

# Catatan untuk Home Server / Nginx Reverse Proxy:
# Jika frontend dan backend diakses lewat 1 domain/IP yang sama, gunakan:
# VITE_RPC_URL=/api/rpc/
```

---

## 🚀 Cara Menjalankan (Development)

1. Masuk ke direktori `frontend`:
   ```bash
   cd frontend
   ```

2. Pasang dependensi:
   ```bash
   npm install
   ```

3. Jalankan server pengembang (Vite Dev Server):
   ```bash
   npm run dev
   ```

4. Buka di browser:
   `http://localhost:5173`

---

## 📦 Build untuk Production / Home Server

Untuk menghasilkan bundle statis yang siap di-serve oleh Nginx, Caddy, atau web server lainnya:

```bash
npm run build
```
File hasil kompilasi akan berada di folder `dist/`.

Uji coba hasil build lokal:
```bash
npm run preview
```

---

## 🐳 Deployment Menggunakan Docker

Proyek ini telah dilengkapi dengan `Dockerfile` multi-stage:
1. **Stage 1 (Build)**: Node.js 20 me-build bundle React Vite.
2. **Stage 2 (Production Server)**: Nginx Alpine yang sangat ringan me-serve folder `dist/` dan otomatis mem-proxy request `/api/` ke backend.

Container frontend dapat langsung dijalankan melalui `docker compose` di root project:
```bash
# Dari root directory
docker compose up --build -d frontend
```
Port default frontend pada Docker: `http://localhost:3000` (atau `http://<IP_HOME_SERVER>:3000`).
