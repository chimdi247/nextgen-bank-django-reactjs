import http from 'k6/http';
import { sleep } from 'k6';
import { MAILPIT_URL } from './config.js';

const q = (email) => encodeURIComponent(`to:${email}`);

/** Remove old mail for a recipient so the next message found is certainly the one we just triggered. */
export function clearMailbox(email) {
  http.del(`${MAILPIT_URL}/api/v1/search?query=${q(email)}`, null, { tags: { ep: 'mailpit', name: 'DELETE mailpit search' } });
}

/** Poll Mailpit until a message to `email` arrives, then return its 6-digit code (or null on timeout). */
export function waitForOtp(email, timeoutSeconds = 40) {
  const deadline = Date.now() + timeoutSeconds * 1000;
  while (Date.now() < deadline) {
    const res = http.get(`${MAILPIT_URL}/api/v1/search?query=${q(email)}&limit=1`, { tags: { ep: 'mailpit', name: 'GET mailpit search' } });
    const msg = res.status === 200 && res.json('messages') && res.json('messages')[0];
    if (msg) {
      const body = http.get(`${MAILPIT_URL}/api/v1/message/${msg.ID}`, { tags: { ep: 'mailpit', name: 'GET mailpit message' } }).json();
      const m = /(?<!\d)(\d{6})(?!\d)/.exec(body.Text || body.HTML || '');
      if (m) return m[1];
    }
    sleep(0.5);
  }
  return null;
}
