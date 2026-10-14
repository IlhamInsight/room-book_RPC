import axios from "axios";

// Target endpoint for JSON-RPC 2.0
// Uses relative /api/rpc/ in production build, or configurable via VITE_RPC_URL
export const RPC_URL =
  import.meta.env.VITE_RPC_URL ||
  (import.meta.env.PROD ? "/api/rpc/" : "http://localhost:8000/api/rpc/");

const rpcHttp = axios.create({
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Executes a Remote Procedure Call (JSON-RPC 2.0).
 *
 * @param {string} method - The remote procedure name (e.g. 'room.get_list', 'auth.login')
 * @param {object} params - Parameters object for the procedure
 * @returns {Promise<any>} - The result returned from the remote procedure
 */
export async function callRPC(method, params = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const requestId = Date.now() + Math.floor(Math.random() * 1000);

  const payload = {
    jsonrpc: "2.0",
    method: method,
    params: params || {},
    id: requestId,
  };

  if (import.meta.env.VITE_DEBUG) {
    console.log(`[RPC Request] --> ${method} (id: ${requestId})`, params);
  }

  try {
    const response = await rpcHttp.post(RPC_URL, payload, { headers });

    if (import.meta.env.VITE_DEBUG) {
      console.log(`[RPC Response] <-- ${method} (id: ${requestId})`, response.data);
    }

    // Check for JSON-RPC 2.0 standard error
    if (response.data && response.data.error) {
      const { code, message, data } = response.data.error;
      const error = new Error(message || "RPC Remote Procedure Error");
      error.code = code;
      error.data = data;

      if (code === -32001 || code === 401) {
        console.warn("[RPC] Unauthorized error received. Clearing token.");
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        window.dispatchEvent(new Event("auth:unauthorized"));
      }

      throw error;
    }

    return response.data ? response.data.result : null;
  } catch (err) {
    if (err.response && (err.response.status === 401 || err.response.status === 403)) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.dispatchEvent(new Event("auth:unauthorized"));
    }

    if (err.code && err.message) {
      throw err;
    }

    const netError = new Error(
      err.response?.data?.error?.message ||
        err.response?.data?.message ||
        err.message ||
        "Gagal terhubung ke RPC Server"
    );
    throw netError;
  }
}

export default {
  call: callRPC,
  RPC_URL,
};
