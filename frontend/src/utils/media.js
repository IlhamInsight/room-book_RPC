/**
 * Utility to resolve media URLs (avatars, room images, payment proofs, etc.)
 * Handles:
 * - Null / empty paths
 * - Base64 data URLs ('data:image/...') and Blob URLs ('blob:...')
 * - Relative media paths ('/media/avatars/...', 'avatars/...')
 * - Stale absolute localhost URLs stored in database / localStorage when hosted remotely
 * - Full external CDN URLs (e.g., Unsplash)
 */
export function getMediaUrl(path) {
  if (!path) return null;

  // Base64 data preview or blob object URL
  if (typeof path === 'string' && (path.startsWith('data:') || path.startsWith('blob:'))) {
    return path;
  }

  // Determine backend origin base
  let backendOrigin = '';
  const apiUrl = import.meta.env.VITE_API_URL;
  const rpcUrl = import.meta.env.VITE_RPC_URL;

  if (apiUrl && apiUrl.startsWith('http')) {
    backendOrigin = apiUrl.replace(/\/api\/?$/, '');
  } else if (rpcUrl && rpcUrl.startsWith('http')) {
    backendOrigin = rpcUrl.replace(/\/api\/rpc\/?$/, '').replace(/\/api\/?$/, '');
  } else if (!import.meta.env.PROD) {
    backendOrigin = 'http://localhost:8000';
  } else {
    // In production build with reverse proxy (Nginx routes /media/ and /api/ on same host)
    backendOrigin = '';
  }

  // If path is an absolute URL pointing to localhost/internal docker container,
  // but the client is viewing the site on a remote domain/host:
  if (path.startsWith('http://') || path.startsWith('https://')) {
    try {
      const urlObj = new URL(path);
      const isInternalHost =
        urlObj.hostname === 'localhost' ||
        urlObj.hostname === '127.0.0.1' ||
        urlObj.hostname === 'booking_rpc_backend' ||
        urlObj.hostname === 'backend';

      const isClientRemote =
        typeof window !== 'undefined' &&
        window.location.hostname !== 'localhost' &&
        window.location.hostname !== '127.0.0.1';

      if (isInternalHost && isClientRemote) {
        const relativePath = urlObj.pathname + urlObj.search;
        return backendOrigin ? `${backendOrigin}${relativePath}` : relativePath;
      }
      return path;
    } catch {
      return path;
    }
  }

  // Ensure path starts with /media/ if stored as relative path (e.g. 'avatars/...')
  let cleanPath = path;
  if (!cleanPath.startsWith('/')) {
    cleanPath = cleanPath.startsWith('media/') ? `/${cleanPath}` : `/media/${cleanPath}`;
  }

  return backendOrigin ? `${backendOrigin}${cleanPath}` : cleanPath;
}

export default getMediaUrl;
