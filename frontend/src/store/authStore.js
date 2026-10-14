import { create } from "zustand";
import { callRPC } from "../utils/rpcClient";

export const useAuthStore = create((set) => ({
  user: JSON.parse(localStorage.getItem("user")) || null,
  token: localStorage.getItem("token") || null,
  isAuthenticated: !!localStorage.getItem("token"),
  isLoading: false,
  error: null,

  unreadNotifications: 0,

  login: async (credentials) => {
    set({ isLoading: true, error: null });
    try {
      // Remote Procedure Call: auth.login
      const result = await callRPC("auth.login", credentials);
      const { access, user } = result;

      localStorage.setItem("token", access);
      localStorage.setItem("user", JSON.stringify(user));
      set({
        user: user,
        token: access,
        isAuthenticated: true,
        isLoading: false,
      });
      
      // Fetch unread count after login
      useAuthStore.getState().fetchUnreadCount();
      
      return true;
    } catch (error) {
      set({
        error: error.message || "Login failed. Please check your credentials.",
        isLoading: false,
      });
      return false;
    }
  },

  register: async (userData) => {
    set({ isLoading: true, error: null });
    try {
      // Remote Procedure Call: auth.register
      await callRPC("auth.register", userData);
      set({ isLoading: false });
      return true;
    } catch (error) {
      set({
        error: error.message || "Registration failed.",
        isLoading: false,
      });
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    set({ user: null, token: null, isAuthenticated: false, unreadNotifications: 0 });
  },

  // Used for fetching initial user profile if token exists
  fetchProfile: async () => {
    if (!localStorage.getItem("token")) return;
    
    try {
      // Remote Procedure Call: auth.get_profile
      const userData = await callRPC("auth.get_profile");
      localStorage.setItem("user", JSON.stringify(userData));
      set({ user: userData, isAuthenticated: true });
      
      // Fetch unread count
      useAuthStore.getState().fetchUnreadCount();
    } catch (error) {
      console.error("Failed to fetch profile via RPC", error);
      if (error.code === -32001 || error.code === 401) {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        set({ user: null, token: null, isAuthenticated: false });
      }
    }
  },

  fetchUnreadCount: async () => {
    try {
      // Remote Procedure Call: notification.get_unread_count
      const result = await callRPC("notification.get_unread_count");
      set({ unreadNotifications: result ? result.unread_count : 0 });
    } catch (error) {
      console.error("Failed to fetch unread count via RPC", error);
    }
  },
}));

// Listen for unauthorized events to auto logout
if (typeof window !== "undefined") {
  window.addEventListener("auth:unauthorized", () => {
    useAuthStore.getState().logout();
  });
}
