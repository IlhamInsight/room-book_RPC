import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { LogOut, Bell, Menu, X } from 'lucide-react';
import { getMediaUrl } from '../../utils/media';

export default function Navbar() {
  const { isAuthenticated, logout, user, unreadNotifications, fetchUnreadCount } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      fetchUnreadCount();
      
      // Real-time update: poll for new notifications every 30 seconds
      const interval = setInterval(() => {
        fetchUnreadCount();
      }, 30000);
      
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, fetchUnreadCount]);

  return (
    <nav className="glass sticky top-0 z-50 px-6 py-4">
      <div className="flex items-center justify-between max-w-7xl mx-auto w-full">
        <Link to="/" className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          RoomBook
        </Link>
        
        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-6">
          <Link to="/rooms" className="text-slate-600 hover:text-blue-600 transition-colors font-medium">Rooms</Link>
          
          {isAuthenticated ? (
            <>
              <Link to="/dashboard" className="text-slate-600 hover:text-blue-600 transition-colors font-medium">Dashboard</Link>
              <Link to="/notifications" className="text-slate-600 hover:text-blue-600 transition-colors relative">
                <Bell className="w-5 h-5" />
                {unreadNotifications > 0 && (
                  <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center animate-pulse">
                    {unreadNotifications > 9 ? '9+' : unreadNotifications}
                  </span>
                )}
              </Link>
              <div className="flex items-center gap-4">
                {user?.profile?.role === 'admin' && (
                  <Link to="/admin" className="flex items-center gap-1.5 px-4 py-2 bg-slate-100 text-slate-700 rounded-full text-sm font-bold hover:bg-slate-200 transition-all border border-slate-200">
                    Manage
                  </Link>
                )}
                <Link to="/profile" className="flex items-center gap-2 text-slate-700 hover:text-blue-600 font-medium group">
                  <div className="w-8 h-8 rounded-full bg-slate-200 overflow-hidden border border-slate-200 transition-transform group-hover:scale-105">
                    {user?.profile?.avatar ? (
                      <img 
                        src={getMediaUrl(user.profile.avatar)} 
                        alt="avatar" 
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          e.target.style.display = 'none';
                          const fallback = e.target.parentElement?.querySelector('.avatar-fallback');
                          if (fallback) fallback.classList.remove('hidden');
                        }}
                      />
                    ) : null}
                    <div className={`avatar-fallback w-full h-full flex items-center justify-center bg-blue-100 text-blue-600 text-xs font-bold ${user?.profile?.avatar ? 'hidden' : ''}`}>
                      {(user?.full_name?.[0] || user?.username?.[0] || 'U').toUpperCase()}
                    </div>
                  </div>
                  <span className="hidden sm:inline">{user?.full_name || user?.username || 'Profile'}</span>
                </Link>
                <button onClick={logout} className="text-red-500 hover:text-red-600 transition-colors cursor-pointer">
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-4">
              <Link to="/login" className="text-slate-600 hover:text-blue-600 font-medium transition-colors">Login</Link>
              <Link to="/register" className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-full font-medium transition-all shadow-md hover:shadow-lg">
                Sign Up
              </Link>
            </div>
          )}
        </div>

        {/* Mobile Navigation controls */}
        <div className="flex items-center gap-4 md:hidden">
          {isAuthenticated && (
            <Link to="/notifications" className="text-slate-600 hover:text-blue-600 transition-colors relative mr-1">
              <Bell className="w-5 h-5" />
              {unreadNotifications > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center animate-pulse">
                  {unreadNotifications > 9 ? '9+' : unreadNotifications}
                </span>
              )}
            </Link>
          )}
          <button 
            onClick={() => setIsOpen(!isOpen)} 
            className="text-slate-600 hover:text-slate-900 focus:outline-none cursor-pointer"
          >
            {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Dropdown Menu */}
      {isOpen && (
        <div className="md:hidden mt-4 pt-4 border-t border-slate-200/50 flex flex-col gap-4 animate-in fade-in slide-in-from-top duration-200">
          <Link 
            to="/rooms" 
            onClick={() => setIsOpen(false)} 
            className="text-slate-600 hover:text-blue-600 transition-colors font-medium py-1"
          >
            Rooms
          </Link>
          
          {isAuthenticated ? (
            <>
              <Link 
                to="/dashboard" 
                onClick={() => setIsOpen(false)} 
                className="text-slate-600 hover:text-blue-600 transition-colors font-medium py-1"
              >
                Dashboard
              </Link>
              {user?.profile?.role === 'admin' && (
                <Link 
                  to="/admin" 
                  onClick={() => setIsOpen(false)} 
                  className="flex items-center gap-1.5 px-4 py-2 bg-slate-100 text-slate-700 rounded-xl text-sm font-bold hover:bg-slate-200 transition-all border border-slate-200 w-fit"
                >
                  Manage System
                </Link>
              )}
              <Link 
                to="/profile" 
                onClick={() => setIsOpen(false)} 
                className="flex items-center gap-2 text-slate-700 hover:text-blue-600 font-medium py-1"
              >
                <div className="w-8 h-8 rounded-full bg-slate-200 overflow-hidden border border-slate-200">
                  {user?.profile?.avatar ? (
                    <img 
                      src={getMediaUrl(user.profile.avatar)} 
                      alt="avatar" 
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        const fallback = e.target.parentElement?.querySelector('.avatar-fallback');
                        if (fallback) fallback.classList.remove('hidden');
                      }}
                    />
                  ) : null}
                  <div className={`avatar-fallback w-full h-full flex items-center justify-center bg-blue-100 text-blue-600 text-xs font-bold ${user?.profile?.avatar ? 'hidden' : ''}`}>
                    {(user?.full_name?.[0] || user?.username?.[0] || 'U').toUpperCase()}
                  </div>
                </div>
                <span>{user?.full_name || user?.username || 'Profile'}</span>
              </Link>
              <button 
                onClick={() => {
                  logout();
                  setIsOpen(false);
                }} 
                className="text-red-500 hover:text-red-600 transition-colors font-medium flex items-center gap-2 py-1 text-left w-full cursor-pointer"
              >
                <LogOut className="w-5 h-5" />
                <span>Logout</span>
              </button>
            </>
          ) : (
            <div className="flex flex-col gap-3 pt-2">
              <Link 
                to="/login" 
                onClick={() => setIsOpen(false)} 
                className="text-slate-600 hover:text-blue-600 font-medium transition-colors py-1"
              >
                Login
              </Link>
              <Link 
                to="/register" 
                onClick={() => setIsOpen(false)} 
                className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-medium transition-all shadow-md hover:shadow-lg text-center w-full"
              >
                Sign Up
              </Link>
            </div>
          )}
        </div>
      )}
    </nav>
  );
}
