import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
  // 90s: Render's free tier cold-starts in ~65s, well past the old 30s budget,
  // so the first request after idle no longer times out before the server wakes
  // (remediation brief P0-1).
  timeout: 90000,
});

if (import.meta.env.PROD && !import.meta.env.VITE_API_URL) {
  console.warn('VITE_API_URL not set - using localhost fallback in production!');
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      console.error('Request timeout');
    } else if (!error.response) {
      console.error('Network error - backend may be unreachable');
    }
    return Promise.reject(error);
  }
);

/**
 * Fire a non-blocking health check on app mount to start Render's cold-start
 * wake-up as early as possible, so the backend is likely warm by the time the
 * user submits a statement. Failures are ignored on purpose (P0-1).
 */
export function warmUpBackend(): void {
  api.get('/health').catch(() => {});
}

/** Best-effort delete of a session's server-side data, on exit (P0-4). */
export function deleteSession(sessionId: string): void {
  api.delete(`/session/${sessionId}`).catch(() => {});
}

/**
 * Does this session still hold data server-side?
 *
 * Used to validate a session id restored from sessionStorage after a page
 * reload: the id survives the refresh but the server-side data may have already
 * been reaped (30-minute TTL) or deleted, and rendering a dashboard whose every
 * module 404s is worse than returning to the upload screen.
 *
 * `/subscriptions` is the cheapest read that is session-scoped; it answers 404
 * once the session is gone. A network/timeout failure resolves TRUE so a cold
 * backend does not throw away a session that is probably still there.
 */
export async function sessionExists(sessionId: string): Promise<boolean> {
  try {
    await api.get('/subscriptions', { headers: { 'X-Session-Id': sessionId } });
    return true;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response) {
      return err.response.status !== 404;
    }
    return true;
  }
}

export default api;
