/** Public site key endpoint. The secret key never leaves the server. */
module.exports = function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({error:'Only GET is supported.'});
  }
  const siteKey = process.env.TURNSTILE_SITE_KEY;
  if (!siteKey) return res.status(503).json({error:'Security verification is not configured yet.'});
  return res.status(200).json({siteKey});
};
