import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Check, Calendar, Clock, CreditCard, ChevronRight, Loader2, AlertCircle, Info } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../utils/api';
import { useRoomStore } from '../store/roomStore';
import { useAuthStore } from '../store/authStore';

export default function BookingPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { getRoomById, rooms, fetchRooms } = useRoomStore();
  const { fetchUnreadCount } = useAuthStore();
  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCheckingAvailability, setIsCheckingAvailability] = useState(false);
  const [formData, setFormData] = useState({
    date: '',
    startTime: '',
    endTime: '',
    notes: '',
    paymentMethod: 'transfer'
  });

  useEffect(() => {
    if (rooms.length === 0) {
      fetchRooms();
    }
  }, [fetchRooms, rooms.length]);

  const room = getRoomById(id);

  // Kalkulasi & Validasi Jam Booking (Mendukung Booking Normal, Lewat Tengah Malam, dan Tepat 24 Jam Penuh)
  const getBookingCalculation = () => {
    const startTime = (formData.startTime || '').trim();
    const endTime = (formData.endTime || '').trim();
    const pricePerHour = room?.price || parseFloat(room?.price_per_hour) || 0;

    if (!startTime || !endTime) {
      return { 
        isReady: false,
        isValid: false, 
        message: 'Silakan pilih waktu mulai dan waktu selesai.' 
      };
    }

    const [startH, startM] = startTime.split(':').map(Number);
    const [endH, endM] = endTime.split(':').map(Number);

    const startMinutes = startH * 60 + (startM || 0);
    const endMinutes = endH * 60 + (endM || 0);

    let diffMinutes = 0;
    let isOvernight = false;
    let is24Hours = false;

    if (endMinutes < startMinutes) {
      // Lewat tengah malam (overnight): selesai keesokan harinya
      diffMinutes = (24 * 60 - startMinutes) + endMinutes;
      isOvernight = true;
    } else if (endMinutes === startMinutes) {
      // Waktu sama persis dihitung tepat 24 jam (1 hari penuh keesokan harinya)
      diffMinutes = 24 * 60;
      isOvernight = true;
      is24Hours = true;
    } else {
      diffMinutes = endMinutes - startMinutes;
      isOvernight = false;
    }

    if (diffMinutes < 30) {
      return { 
        isReady: true,
        isValid: false, 
        message: 'Durasi pemesanan minimal adalah 30 menit (0.5 jam).' 
      };
    }

    if (diffMinutes > 24 * 60) {
      return {
        isReady: true,
        isValid: false,
        message: 'Durasi pemesanan maksimal adalah 24 jam.'
      };
    }

    const hours = Math.floor(diffMinutes / 60);
    const minutes = diffMinutes % 60;
    const durationHours = parseFloat((diffMinutes / 60).toFixed(2));
    const totalPrice = Math.round(durationHours * pricePerHour);

    let durationLabel = '';
    if (is24Hours) {
      durationLabel = '24 Jam (1 Hari Penuh)';
    } else if (hours > 0 && minutes > 0) {
      durationLabel = `${hours} Jam ${minutes} Menit (${durationHours} Jam)`;
    } else if (hours > 0) {
      durationLabel = `${hours} Jam`;
    } else {
      durationLabel = `${minutes} Menit (${durationHours} Jam)`;
    }

    if (isOvernight && !is24Hours) {
      durationLabel += ' • Lewat Tengah Malam';
    }

    return {
      isReady: true,
      isValid: true,
      isOvernight,
      is24Hours,
      diffMinutes,
      durationHours,
      hours,
      minutes,
      durationLabel,
      pricePerHour,
      totalPrice
    };
  };

  const calc = getBookingCalculation();

  const handleNext = async () => {
    if (step === 1) {
      if (!formData.date || !formData.startTime || !formData.endTime) {
        toast.error('Mohon isi tanggal, waktu mulai, dan waktu selesai');
        return;
      }

      if (!calc.isValid) {
        toast.error(calc.message || 'Waktu pemesanan tidak valid');
        return;
      }

      // Check availability (includes blackout date & time conflict check)
      setIsCheckingAvailability(true);
      try {
        const response = await api.get(`/rooms/${id}/check_availability/`, {
          params: { date: formData.date, start_time: formData.startTime, end_time: formData.endTime }
        });
        if (!response.data.available) {
          toast.error(response.data.reason || 'Ruangan tidak tersedia pada waktu ini');
          setIsCheckingAvailability(false);
          return;
        }
      } catch (error) {
        toast.error(error.message || 'Gagal memeriksa ketersediaan ruangan');
        setIsCheckingAvailability(false);
        return;
      } finally {
        setIsCheckingAvailability(false);
      }
    }
    setStep(s => Math.min(s + 1, 3));
  };

  const handlePrev = () => setStep(s => Math.max(s - 1, 1));
  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

  const handleBook = async () => {
    if (!calc.isValid) {
      toast.error(calc.message || 'Waktu pemesanan tidak valid');
      return;
    }
    setIsSubmitting(true);
    try {
      const payload = {
        room: id,
        booking_date: formData.date,
        start_time: formData.startTime,
        end_time: formData.endTime,
        notes: formData.notes
      };

      const response = await api.post('/bookings/', payload);
      const booking = response.data;

      // Refresh notification count
      fetchUnreadCount();

      toast.success('Pemesanan ruangan berhasil dikonfirmasi! 🎉');
      
      // Redirect to payment page with the REAL booking ID from backend
      setTimeout(() => {
        navigate(`/payment/${booking.id}`);
      }, 1500);
    } catch (error) {
      console.error('Booking failed', error);
      const errorMsg = error.message || error.response?.data?.message || 'Gagal memproses pemesanan';
      toast.error(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!room) {
    return (
      <div className="min-h-[400px] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-12">
      <div className="mb-8 sm:mb-10 text-center">
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">Reservasi Ruangan</h1>
        <p className="text-sm sm:text-base text-slate-500 mt-2">
          {room.name} — Rp {(room.price || 0).toLocaleString('id-ID')}/jam
        </p>
      </div>

      {/* Stepper */}
      <div className="flex items-center justify-center mb-8 sm:mb-12">
        <div className="flex items-center w-full max-w-2xl">
          <div className="flex flex-col items-center flex-1">
            <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center font-bold text-sm sm:text-base ${step >= 1 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}`}>1</div>
            <span className="text-[10px] sm:text-sm mt-2 font-medium text-slate-700 text-center">Waktu & Durasi</span>
          </div>
          <div className={`h-1 flex-1 ${step >= 2 ? 'bg-blue-600' : 'bg-slate-200'}`}></div>
          <div className="flex flex-col items-center flex-1">
            <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center font-bold text-sm sm:text-base ${step >= 2 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}`}>2</div>
            <span className="text-[10px] sm:text-sm mt-2 font-medium text-slate-700 text-center">Detail & Catatan</span>
          </div>
          <div className={`h-1 flex-1 ${step >= 3 ? 'bg-blue-600' : 'bg-slate-200'}`}></div>
          <div className="flex flex-col items-center flex-1">
            <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center font-bold text-sm sm:text-base ${step >= 3 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}`}>3</div>
            <span className="text-[10px] sm:text-sm mt-2 font-medium text-slate-700 text-center">Konfirmasi</span>
          </div>
        </div>
      </div>

      <div className="bg-white p-4 sm:p-8 rounded-3xl shadow-sm border border-slate-100 min-h-[400px] relative">
        {step === 1 && (
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
              <Calendar className="text-blue-500" /> Pilih Tanggal & Waktu Penggunaan
            </h2>
            
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">Tanggal Pemesanan</label>
                <input 
                  type="date" 
                  name="date"
                  value={formData.date}
                  onChange={handleChange}
                  min={new Date().toISOString().split('T')[0]}
                  className="w-full p-3 sm:p-4 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none" 
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">Waktu Mulai</label>
                  <input 
                    type="time" 
                    name="startTime"
                    value={formData.startTime}
                    onChange={handleChange}
                    className="w-full p-3 sm:p-4 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none" 
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">Waktu Selesai</label>
                  <input 
                    type="time" 
                    name="endTime"
                    value={formData.endTime}
                    onChange={handleChange}
                    className="w-full p-3 sm:p-4 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none" 
                  />
                </div>
              </div>
            </div>

            {/* Kotak Rincian & Kalkulasi Jam Pemesanan */}
            <div className="pt-2">
              {calc.isReady && calc.isValid ? (
                <div className="p-4 sm:p-5 rounded-2xl bg-blue-50/80 border border-blue-200 text-slate-800 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-bold text-blue-900 text-sm sm:text-base">
                      Rincian Durasi & Estimasi Biaya:
                    </div>
                    {calc.isOvernight && (
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700 border border-indigo-200">
                        {calc.is24Hours ? '24 Jam Penuh (+1 Hari)' : 'Lewat Tengah Malam (+1 Hari)'}
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                    <div className="bg-white p-3 rounded-xl border border-blue-100">
                      <span className="text-slate-500 block text-xs">Total Durasi</span>
                      <span className="font-bold text-slate-800 text-base">{calc.durationLabel}</span>
                    </div>
                    <div className="bg-white p-3 rounded-xl border border-blue-100">
                      <span className="text-slate-500 block text-xs">Tarif Ruangan</span>
                      <span className="font-bold text-slate-800 text-base">Rp {calc.pricePerHour.toLocaleString('id-ID')} / jam</span>
                    </div>
                    <div className="bg-white p-3 rounded-xl border border-blue-100">
                      <span className="text-slate-500 block text-xs">Kalkulasi Subtotal</span>
                      <span className="font-extrabold text-blue-600 text-base">
                        {calc.durationHours} jam × Rp {calc.pricePerHour.toLocaleString('id-ID')} = Rp {calc.totalPrice.toLocaleString('id-ID')}
                      </span>
                    </div>
                  </div>
                  {calc.isOvernight && (
                    <p className="text-xs text-indigo-700 bg-indigo-50/70 p-2.5 rounded-lg border border-indigo-100">
                      Pemesanan dimulai pukul <strong>{formData.startTime} WIB</strong> dan selesai pada <strong>keesokan harinya pukul {formData.endTime} WIB</strong>{calc.is24Hours ? ' (durasi tepat 24 jam penuh).' : '.'}
                    </p>
                  )}
                </div>
              ) : calc.isReady && !calc.isValid ? (
                <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-red-700 flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold block">Waktu Tidak Valid:</span>
                    <span className="text-sm">{calc.message}</span>
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-slate-500 flex items-center gap-3 text-sm">
                  <Info className="w-5 h-5 text-slate-400 shrink-0" />
                  <span>Pilih tanggal, jam mulai, dan jam selesai untuk melihat durasi dan kalkulasi biaya.</span>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {step === 2 && (
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">Detail & Catatan Pemesanan</h2>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Catatan Khusus / Keperluan</label>
              <textarea 
                name="notes"
                value={formData.notes}
                onChange={handleChange}
                rows="4" 
                className="w-full p-4 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                placeholder="Contoh: Tolong siapkan meja dengan susunan U-shape dan proyektor HDMI"
              ></textarea>
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Metode Pembayaran</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div 
                  onClick={() => setFormData({...formData, paymentMethod: 'transfer'})}
                  className={`p-4 rounded-xl border-2 cursor-pointer flex items-center gap-3 transition-colors ${formData.paymentMethod === 'transfer' ? 'border-blue-600 bg-blue-50' : 'border-slate-200 hover:border-blue-300'}`}
                >
                  <CreditCard className={formData.paymentMethod === 'transfer' ? 'text-blue-600' : 'text-slate-400'} />
                  <div>
                    <span className="font-bold block">Transfer Bank</span>
                    <span className="text-xs text-slate-500">Upload bukti transfer setelah booking</span>
                  </div>
                </div>
                <div 
                  onClick={() => setFormData({...formData, paymentMethod: 'cash'})}
                  className={`p-4 rounded-xl border-2 cursor-pointer flex items-center gap-3 transition-colors ${formData.paymentMethod === 'cash' ? 'border-blue-600 bg-blue-50' : 'border-slate-200 hover:border-blue-300'}`}
                >
                  <CreditCard className={formData.paymentMethod === 'cash' ? 'text-blue-600' : 'text-slate-400'} />
                  <div>
                    <span className="font-bold block">Bayar di Tempat</span>
                    <span className="text-xs text-slate-500">Pembayaran tunai langsung ke kasir/resepsionis</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {step === 3 && (
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
              <Check className="text-green-500" /> Tinjau & Konfirmasi Pemesanan
            </h2>
            
            <div className="bg-slate-50 p-4 sm:p-6 rounded-2xl border border-slate-200 space-y-4">
              <div className="flex justify-between items-center pb-3 border-b border-slate-200">
                <span className="text-slate-500 text-sm sm:text-base">Ruangan</span>
                <span className="font-bold text-slate-900 text-sm sm:text-base text-right">{room.name}</span>
              </div>
              <div className="flex justify-between items-center pb-3 border-b border-slate-200">
                <span className="text-slate-500 text-sm sm:text-base">Tanggal Penggunaan</span>
                <span className="font-medium text-slate-900 text-sm sm:text-base text-right">{formData.date}</span>
              </div>
              <div className="flex justify-between items-center pb-3 border-b border-slate-200">
                <span className="text-slate-500 text-sm sm:text-base">Waktu & Jam</span>
                <div className="text-right">
                  <span className="font-medium text-slate-900 text-sm sm:text-base block">
                    {formData.startTime} - {formData.endTime} WIB
                  </span>
                  {calc.isOvernight && (
                    <span className="text-xs text-indigo-600 font-semibold block">
                      {calc.is24Hours 
                        ? `24 Jam Penuh (Selesai Besok Pukul ${formData.endTime} WIB)`
                        : `Lewat Tengah Malam (Selesai Besok Pukul ${formData.endTime} WIB)`}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex justify-between items-center pb-3 border-b border-slate-200">
                <span className="text-slate-500 text-sm sm:text-base">Total Durasi</span>
                <span className="font-semibold text-blue-700 text-sm sm:text-base text-right">{calc.durationLabel}</span>
              </div>
              <div className="flex justify-between items-center pb-3 border-b border-slate-200">
                <span className="text-slate-500 text-sm sm:text-base">Tarif per Jam</span>
                <span className="font-medium text-slate-900 text-sm sm:text-base">Rp {(room.price || 0).toLocaleString('id-ID')} / jam</span>
              </div>
              <div className="flex justify-between items-center pb-3 border-b border-slate-200">
                <span className="text-slate-500 text-sm sm:text-base">Metode Pembayaran</span>
                <span className="font-medium text-slate-900 text-sm sm:text-base capitalize">
                  {formData.paymentMethod === 'transfer' ? 'Transfer Bank' : 'Bayar di Lokasi'}
                </span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <div>
                  <span className="text-base sm:text-lg font-bold text-slate-900 block">Total Biaya</span>
                  <span className="text-xs text-slate-500">({calc.durationHours} jam × Rp {(room.price || 0).toLocaleString('id-ID')})</span>
                </div>
                <span className="text-xl sm:text-2xl font-extrabold text-blue-600">
                  Rp {(calc.totalPrice || 0).toLocaleString('id-ID')}
                </span>
              </div>
            </div>
            
            <label className="flex items-center gap-3 mt-4">
              <input type="checkbox" className="w-5 h-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer" required defaultChecked />
              <span className="text-xs sm:text-sm text-slate-600">Saya menyetujui syarat & ketentuan serta kebijakan pembatalan reservasi.</span>
            </label>
          </motion.div>
        )}

        {/* Footer Actions */}
        <div className="mt-10 flex justify-between pt-6 border-t border-slate-100">
          <button 
            onClick={step === 1 ? () => navigate(`/rooms/${id}`) : handlePrev}
            disabled={isSubmitting}
            className="px-4 sm:px-6 py-2.5 sm:py-3 rounded-xl font-medium text-sm sm:text-base text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            Kembali
          </button>
          
          {step < 3 ? (
            <button 
              onClick={handleNext}
              disabled={isCheckingAvailability}
              className="px-6 sm:px-8 py-2.5 sm:py-3 rounded-xl font-semibold text-sm sm:text-base text-white bg-blue-600 hover:bg-blue-700 transition-colors flex items-center gap-2 disabled:opacity-70 cursor-pointer"
            >
              {isCheckingAvailability ? <><Loader2 className="w-5 h-5 animate-spin" /> Mengecek Jadwal...</> : <>Lanjutkan <ChevronRight size={18} /></>}
            </button>
          ) : (
            <button 
              onClick={handleBook}
              disabled={isSubmitting}
              className="px-6 sm:px-8 py-2.5 sm:py-3 rounded-xl font-bold text-sm sm:text-base text-white bg-gradient-to-r from-blue-600 to-purple-600 hover:shadow-lg transition-all disabled:opacity-70 flex items-center gap-2 cursor-pointer"
            >
              {isSubmitting ? <><Loader2 className="w-5 h-5 animate-spin" /> Memproses...</> : 'Konfirmasi Pemesanan'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
