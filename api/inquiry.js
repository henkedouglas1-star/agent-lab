/** Vercel Node.js function for sponsorship / topic inquiries.
 *  Configure RESEND_API_KEY, INQUIRY_TO_EMAIL, INQUIRY_FROM_EMAIL in Vercel.
 *  No data is stored by this endpoint. Delivery failures are reported honestly.
 */
const limit = new Map();
const WINDOW_MS = 60 * 60 * 1000;
const MAX_REQUESTS_PER_IP = 8;
const types = new Set(['sponsorship', 'topic']);
const clean = (s, max) => typeof s === 'string' ? s.trim().slice(0, max) : '';
const escapeHtml = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({error:'Only POST is supported.'});
  }
  const origin = req.headers.origin;
  const host = req.headers.host;
  if (origin && host) {
    try { if (new URL(origin).host !== host) return res.status(403).json({error:'Invalid request origin.'}); }
    catch { return res.status(403).json({error:'Invalid request origin.'}); }
  }
  let body = req.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch { return res.status(400).json({error:'Invalid JSON.'}); } }
  if (!body || typeof body !== 'object' || Array.isArray(body) || JSON.stringify(body).length > 8000) return res.status(400).json({error:'Invalid inquiry payload.'});

  const type = clean(body.type, 30);
  const name = clean(body.name, 120);
  const email = clean(body.email, 254);
  const company = clean(body.company, 160);
  const interest = clean(body.interest, 160);
  const message = clean(body.message, 3000);
  if (!types.has(type) || !name || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || message.length < 20 || (type === 'sponsorship' && (!company || !interest))) {
    return res.status(400).json({error:'Please provide all required fields and a valid email.'});
  }
  // Instance-local throttle. Add an edge/WAF or durable distributed rate limiter for production scale.
  const ip = String(req.headers['x-forwarded-for'] || req.socket?.remoteAddress || 'unknown').split(',')[0].trim();
  const now = Date.now();
  if (limit.size > 2000) for (const [key, value] of limit) if (now - value.start >= WINDOW_MS) limit.delete(key);
  const entry = limit.get(ip) || {start:now,count:0};
  if (now - entry.start >= WINDOW_MS) { entry.start = now; entry.count = 0; }
  if (++entry.count > MAX_REQUESTS_PER_IP) {
    res.setHeader('Retry-After','3600');
    return res.status(429).json({error:'Too many inquiries. Please try later.'});
  }
  limit.set(ip, entry);

  const { RESEND_API_KEY, INQUIRY_TO_EMAIL, INQUIRY_FROM_EMAIL, TURNSTILE_SECRET_KEY } = process.env;
  if (!RESEND_API_KEY || !INQUIRY_TO_EMAIL || !INQUIRY_FROM_EMAIL) return res.status(503).json({error:'Inquiry delivery is not configured yet.'});
  if (!TURNSTILE_SECRET_KEY) return res.status(503).json({error:'Security verification is not configured yet.'});
  const token = clean(body.turnstileToken, 2048);
  if (!token) return res.status(400).json({error:'Please complete the security verification before submitting.'});
  try {
    const challenge = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({secret:TURNSTILE_SECRET_KEY,response:token,remoteip:ip}),
      signal:AbortSignal.timeout(8000)
    });
    if (!challenge.ok) return res.status(502).json({error:'Security verification is temporarily unavailable. Please try again.'});
    const result = await challenge.json();
    if (result.success !== true || result.hostname !== host || result.action !== 'agent_lab_inquiry') {
      return res.status(403).json({error:'Security verification failed or expired. Please try again.'});
    }
  } catch (e) {
    console.error('Turnstile verification unavailable:', e?.name || 'unknown');
    return res.status(502).json({error:'Security verification is temporarily unavailable. Please try again.'});
  }

  const fields = {Type:type, Name:name, Email:email, Company:company, Interest:interest, Message:message};
  const text = Object.entries(fields).map(([label, val]) => `${label}: ${val || '(not provided)'}`).join('\n\n');
  const html = `<h2>New Agent Lab ${escapeHtml(type)} inquiry</h2>${Object.entries(fields).map(([label, val]) => `<p><b>${escapeHtml(label)}:</b> ${escapeHtml(val || '(not provided)').replace(/\n/g, '<br>')}</p>`).join('')}`;
  try {
    const response = await fetch('https://api.resend.com/emails', {
      method:'POST',
      headers:{'Authorization':`Bearer ${RESEND_API_KEY}`,'Content-Type':'application/json'},
      body:JSON.stringify({from:INQUIRY_FROM_EMAIL,to:[INQUIRY_TO_EMAIL],reply_to:email,subject:`Agent Lab: ${type} inquiry from ${name}`,html,text})
    });
    if (!response.ok) { console.error('Resend inquiry delivery failed', response.status); return res.status(502).json({error:'Email delivery failed. Please try again.'}); }
    return res.status(200).json({ok:true});
  } catch (error) {
    console.error('Resend inquiry network failure', error?.message || 'unknown');
    return res.status(502).json({error:'Email delivery is unavailable. Please try again.'});
  }
};
