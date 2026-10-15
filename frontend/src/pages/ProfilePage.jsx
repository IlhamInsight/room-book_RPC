import { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import { User, Mail, Phone, MapPin, Camera, Save, Lock, X, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../utils/api';
import { getMediaUrl } from '../utils/media';

export default function ProfilePage() {
  const { user } = useAuthStore();
  const [isEditing, setIsEditing] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  
  // Use helper to get the full avatar URL
  const getAvatarUrl = (avatarPath) => getMediaUrl(avatarPath);

  const [formData, setFormData] = useState({
    name: user ? user.full_name || user.username : '',
    email: user?.email || '',
    phone: user?.profile?.phone_number || '',
    address: user?.profile?.address || '',
    avatar: getMediaUrl(user?.profile?.avatar)
  });

  // Sync form data if user loads or updates asynchronously
  useEffect(() => {
    if (user) {
      setFormData((prev) => ({
        ...prev,
        name: user.full_name || user.username || prev.name,
        email: user.email || prev.email,
        phone: user.profile?.phone_number ?? prev.phone,
        address: user.profile?.address ?? prev.address,
        avatar: getMediaUrl(user.profile?.avatar) || prev.avatar,
      }));
    }
  }, [user]);

  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    new_password2: ''
  });
  const [isSubmittingPassword, setIsSubmittingPassword] = useState(false);

  // Mengubah & menyimpan foto profil secara langsung (tanpa harus klik Edit Profile)
  const handleAvatarChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validasi tipe file
    if (!file.type.startsWith('image/')) {
      toast.error('File harus berupa gambar (JPG, PNG, atau WEBP)');
      return;
    }

    // Validasi ukuran file (maksimal 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Ukuran gambar maksimal 5MB');
      return;
    }

    setIsUploadingAvatar(true);
    const toastId = toast.loading('Mengunggah foto profil...');

    try {
      const reader = new FileReader();
      const base64Promise = new Promise((resolve, reject) => {
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
      });
      reader.readAsDataURL(file);
      const base64Data = await base64Promise;

      // Preview langsung di tampilan
      setFormData((prev) => ({ ...prev, avatar: base64Data }));

      // Simpan langsung ke backend via RPC
      const response = await api.patch('/profile/update_profile/', {
        avatar_base64: base64Data,
      });

      const updatedUser = response.data;
      if (updatedUser) {
        useAuthStore.setState({ user: updatedUser });
        localStorage.setItem("user", JSON.stringify(updatedUser));
        
        const newAvatarUrl = getAvatarUrl(updatedUser.profile?.avatar) || base64Data;
        setFormData((prev) => ({
          ...prev,
          avatar: newAvatarUrl,
        }));
      }

      toast.success('Foto profil berhasil diperbarui! 🎉', { id: toastId });
    } catch (error) {
      console.error('Failed to update avatar:', error);
      toast.error(error.message || 'Gagal mengunggah foto profil', { id: toastId });
    } finally {
      setIsUploadingAvatar(false);
      e.target.value = '';
    }
  };

  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const payload = {
        full_name: formData.name,
        email: formData.email,
        phone_number: formData.phone,
        address: formData.address,
      };
      
      const response = await api.patch('/profile/update_profile/', payload);
      const updatedUser = response.data;
      
      // Update store and localStorage
      useAuthStore.setState({ user: updatedUser });
      localStorage.setItem("user", JSON.stringify(updatedUser));
      
      toast.success('Profil berhasil diperbarui!');
      setIsEditing(false);
      
      // Update local form state with new data
      setFormData((prev) => ({
        ...prev,
        name: updatedUser.full_name || updatedUser.username,
        email: updatedUser.email,
        phone: updatedUser.profile?.phone_number || '',
        address: updatedUser.profile?.address || '',
        avatar: getAvatarUrl(updatedUser.profile?.avatar) || prev.avatar
      }));
    } catch (error) {
      toast.error(error.message || 'Gagal memperbarui profil');
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    if (passwordData.new_password !== passwordData.new_password2) {
      toast.error('Password baru tidak cocok');
      return;
    }
    
    setIsSubmittingPassword(true);
    try {
      await api.post('/auth/change-password/', passwordData);
      toast.success('Password berhasil diubah');
      setIsChangingPassword(false);
      setPasswordData({ old_password: '', new_password: '', new_password2: '' });
    } catch (error) {
      toast.error(error.message || 'Gagal mengubah password');
    } finally {
      setIsSubmittingPassword(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-10 w-full">
      <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mb-6 sm:mb-8">Profil Saya</h1>

      <div className="bg-white rounded-3xl border border-slate-100 shadow-sm overflow-hidden">
        {/* Header/Cover */}
        <div className="h-28 sm:h-32 bg-gradient-to-r from-blue-400 to-purple-500 relative">
          <div className="absolute -bottom-10 sm:-bottom-12 left-4 sm:left-8">
            <div className="relative">
              <div className="w-20 h-20 sm:w-24 sm:h-24 bg-white rounded-full p-1 shadow-lg relative">
                <div className="w-full h-full bg-slate-200 rounded-full flex items-center justify-center text-2xl sm:text-3xl font-bold text-slate-500 overflow-hidden relative">
                  {formData.avatar ? (
                    <img 
                      src={formData.avatar} 
                      alt="avatar" 
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        const fallback = e.target.parentElement?.querySelector('.avatar-fallback');
                        if (fallback) fallback.classList.remove('hidden');
                      }}
                    />
                  ) : null}
                  <span className={`avatar-fallback ${formData.avatar ? 'hidden' : ''}`}>
                    {formData.name ? formData.name.charAt(0).toUpperCase() : 'U'}
                  </span>
                  {isUploadingAvatar && (
                    <div className="absolute inset-0 bg-slate-900/50 flex items-center justify-center">
                      <Loader2 size={24} className="text-white animate-spin" />
                    </div>
                  )}
                </div>
              </div>
              <label 
                title="Ganti Foto Profil" 
                className={`absolute bottom-0 right-0 p-2 bg-blue-600 text-white rounded-full shadow-md hover:bg-blue-700 transition-all cursor-pointer ${isUploadingAvatar ? 'opacity-50 cursor-not-allowed' : 'hover:scale-110'}`}
              >
                {isUploadingAvatar ? <Loader2 size={13} className="animate-spin" /> : <Camera size={13} />}
                <input 
                  type="file" 
                  className="hidden" 
                  accept="image/*" 
                  disabled={isUploadingAvatar} 
                  onChange={handleAvatarChange} 
                />
              </label>
            </div>
          </div>
          <div className="absolute top-4 right-4">
            {!isEditing ? (
              <button 
                onClick={() => setIsEditing(true)}
                className="px-3 sm:px-4 py-1.5 sm:py-2 bg-white/20 hover:bg-white/30 backdrop-blur text-white rounded-xl text-xs sm:text-sm font-medium transition-colors cursor-pointer"
              >
                Edit Profil
              </button>
            ) : (
              <button 
                onClick={handleSave}
                disabled={isSaving}
                className="px-3 sm:px-4 py-1.5 sm:py-2 bg-white text-blue-600 rounded-xl text-xs sm:text-sm font-bold shadow-md hover:shadow-lg transition-all flex items-center gap-1.5 disabled:opacity-70 cursor-pointer"
              >
                <Save size={14} /> {isSaving ? 'Menyimpan...' : 'Simpan Perubahan'}
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="pt-12 sm:pt-16 pb-6 sm:pb-8 px-4 sm:px-8">
          <div className="mb-6 sm:mb-8 border-b border-slate-100 pb-6 sm:pb-8">
            <h2 className="text-xl sm:text-2xl font-bold text-slate-900">{formData.name || '-'}</h2>
            <p className="text-sm sm:text-base text-slate-500">{formData.email || '-'}</p>
          </div>

          <div className="space-y-6">
            <h3 className="font-bold text-slate-900 mb-4">Informasi Pribadi</h3>
            
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-500 mb-1">
                <User size={16} /> Nama Lengkap
              </label>
              {isEditing ? (
                <input type="text" name="name" value={formData.name} onChange={handleChange} className="w-full p-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
              ) : (
                <p className="text-slate-900 font-medium">{formData.name || '-'}</p>
              )}
            </div>

            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-500 mb-1">
                <Mail size={16} /> Alamat Email
              </label>
              {isEditing ? (
                <input type="email" name="email" value={formData.email} onChange={handleChange} className="w-full p-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
              ) : (
                <p className="text-slate-900 font-medium">{formData.email || '-'}</p>
              )}
            </div>

            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-500 mb-1">
                <Phone size={16} /> Nomor Telepon
              </label>
              {isEditing ? (
                <input type="tel" name="phone" value={formData.phone} onChange={handleChange} className="w-full p-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
              ) : (
                <p className="text-slate-900 font-medium">{formData.phone || '-'}</p>
              )}
            </div>

            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-500 mb-1">
                <MapPin size={16} /> Alamat
              </label>
              {isEditing ? (
                <textarea name="address" value={formData.address} onChange={handleChange} rows="2" className="w-full p-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none"></textarea>
              ) : (
                <p className="text-slate-900 font-medium">{formData.address || '-'}</p>
              )}
            </div>
          </div>

          <div className="mt-10 pt-8 border-t border-slate-100">
            <h3 className="font-bold text-slate-900 mb-4">Keamanan Akun</h3>
            {!isChangingPassword ? (
              <button 
                onClick={() => setIsChangingPassword(true)}
                className="px-4 py-2 border border-slate-200 text-slate-700 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors flex items-center gap-2 cursor-pointer"
              >
                <Lock size={16} /> Ganti Password
              </button>
            ) : (
              <form onSubmit={handlePasswordSubmit} className="bg-slate-50 p-6 rounded-2xl border border-slate-100 space-y-4 max-w-md">
                <div className="flex justify-between items-center mb-2">
                  <h4 className="font-bold text-slate-900">Ganti Password</h4>
                  <button type="button" onClick={() => setIsChangingPassword(false)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                    <X size={20} />
                  </button>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Password Saat Ini</label>
                  <input 
                    type="password" 
                    required
                    value={passwordData.old_password}
                    onChange={(e) => setPasswordData({...passwordData, old_password: e.target.value})}
                    className="w-full p-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" 
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Password Baru</label>
                  <input 
                    type="password" 
                    required
                    value={passwordData.new_password}
                    onChange={(e) => setPasswordData({...passwordData, new_password: e.target.value})}
                    className="w-full p-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" 
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Konfirmasi Password Baru</label>
                  <input 
                    type="password" 
                    required
                    value={passwordData.new_password2}
                    onChange={(e) => setPasswordData({...passwordData, new_password2: e.target.value})}
                    className="w-full p-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" 
                  />
                </div>
                
                <button 
                  type="submit" 
                  disabled={isSubmittingPassword}
                  className="w-full py-2.5 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors disabled:opacity-70 mt-2 cursor-pointer"
                >
                  {isSubmittingPassword ? 'Memperbarui...' : 'Perbarui Password'}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
