import { callRPC, RPC_URL } from "./rpcClient";

/**
 * Helper to convert File to Base64 data URL
 */
export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = (error) => reject(error);
  });
}

/**
 * Adapter that translates REST-like calls to JSON-RPC 2.0 procedures.
 * This guarantees 100% of network traffic uses the RPC protocol.
 */
const api = {
  callRPC,
  RPC_URL,

  async get(url, config = {}) {
    const params = config.params || {};

    // Match /rooms/:id/check_availability/
    const checkAvailMatch = url.match(/\/rooms\/(\d+)\/check_availability/);
    if (checkAvailMatch) {
      const result = await callRPC("room.check_availability", {
        room_id: parseInt(checkAvailMatch[1]),
        ...params,
      });
      return { data: result };
    }

    // Match /rooms/:id/
    const roomDetailMatch = url.match(/\/rooms\/(\d+)\/?$/);
    if (roomDetailMatch) {
      const result = await callRPC("room.get_detail", {
        id: parseInt(roomDetailMatch[1]),
      });
      return { data: result };
    }

    // Match /rooms/
    if (url.startsWith("/rooms")) {
      const result = await callRPC("room.get_list", params);
      return { data: result };
    }

    // Match /amenities/
    if (url.startsWith("/amenities")) {
      const result = await callRPC("room.get_amenities", params);
      return { data: result };
    }

    // Match /profile/my_profile/
    if (url.includes("my_profile")) {
      const result = await callRPC("auth.get_profile");
      return { data: result };
    }

    // Match /notifications/unread_count/
    if (url.includes("unread_count")) {
      const result = await callRPC("notification.get_unread_count");
      return { data: result };
    }

    // Match /notifications/
    if (url.startsWith("/notifications")) {
      const result = await callRPC("notification.get_list");
      return { data: result };
    }

    // Match /bookings/my_bookings/
    if (url.includes("my_bookings")) {
      const result = await callRPC("booking.get_my_bookings");
      return { data: result };
    }

    // Match /bookings/:id/
    const bookingDetailMatch = url.match(/\/bookings\/(\d+)\/?$/);
    if (bookingDetailMatch) {
      const result = await callRPC("booking.get_detail", {
        id: parseInt(bookingDetailMatch[1]),
      });
      return { data: result };
    }

    // Match /reviews/
    if (url.startsWith("/reviews")) {
      const result = await callRPC("review.get_list", params);
      return { data: result };
    }

    // Default fallback to direct RPC call
    const cleanMethod = url.replace(/^\/+|\/+$/g, "").replace(/\//g, ".");
    const result = await callRPC(cleanMethod, params);
    return { data: result };
  },

  async post(url, data = {}) {
    // Auth login
    if (url.includes("auth/login")) {
      const result = await callRPC("auth.login", data);
      return { data: result };
    }

    // Auth register
    if (url.includes("auth/register")) {
      const result = await callRPC("auth.register", data);
      return { data: result };
    }

    // Change password
    if (url.includes("change-password")) {
      const result = await callRPC("auth.change_password", data);
      return { data: result };
    }

    // Create booking
    if (url.startsWith("/bookings") && !url.includes("cancel")) {
      const result = await callRPC("booking.create", data);
      return { data: result };
    }

    // Cancel booking: /bookings/:id/cancel/
    const cancelMatch = url.match(/\/bookings\/(\d+)\/cancel/);
    if (cancelMatch) {
      const result = await callRPC("booking.cancel", {
        id: parseInt(cancelMatch[1]),
      });
      return { data: result };
    }

    // Submit payment
    if (url.startsWith("/payments")) {
      let payload = {};
      if (data instanceof FormData) {
        for (const [key, val] of data.entries()) {
          if (val instanceof File) {
            payload[key + "_base64"] = await fileToBase64(val);
          } else {
            payload[key] = val;
          }
        }
      } else {
        payload = data;
      }
      const result = await callRPC("payment.submit", payload);
      return { data: result };
    }

    // Create review
    if (url.startsWith("/reviews")) {
      const result = await callRPC("review.create", data);
      return { data: result };
    }

    // Notifications mark_as_read
    const markReadMatch = url.match(/\/notifications\/(\d+)\/mark_as_read/);
    if (markReadMatch) {
      const result = await callRPC("notification.mark_as_read", {
        id: parseInt(markReadMatch[1]),
      });
      return { data: result };
    }

    // Notifications mark_all_as_read
    if (url.includes("mark_all_as_read")) {
      const result = await callRPC("notification.mark_all_as_read");
      return { data: result };
    }

    // Default fallback
    const cleanMethod = url.replace(/^\/+|\/+$/g, "").replace(/\//g, ".");
    const result = await callRPC(cleanMethod, data);
    return { data: result };
  },

  async patch(url, data = {}) {
    if (url.includes("profile")) {
      let payload = {};
      if (data instanceof FormData) {
        for (const [key, val] of data.entries()) {
          if (val instanceof File) {
            payload[key + "_base64"] = await fileToBase64(val);
          } else {
            payload[key] = val;
          }
        }
      } else {
        payload = data;
      }
      const result = await callRPC("auth.update_profile", payload);
      return { data: result };
    }

    const cleanMethod = url.replace(/^\/+|\/+$/g, "").replace(/\//g, ".");
    const result = await callRPC(cleanMethod, data);
    return { data: result };
  },

  async put(url, data = {}) {
    return this.patch(url, data);
  },

  async delete(url, config = {}) {
    const cleanMethod = url.replace(/^\/+|\/+$/g, "").replace(/\//g, ".") + ".delete";
    const result = await callRPC(cleanMethod, config.data || {});
    return { data: result };
  },
};

export { callRPC };
export default api;
