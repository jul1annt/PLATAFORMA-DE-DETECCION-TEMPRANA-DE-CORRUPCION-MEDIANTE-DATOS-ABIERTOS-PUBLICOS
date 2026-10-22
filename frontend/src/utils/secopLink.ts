export function secopSourceUrl(value: unknown): string | null {
  let candidate = value;
  if (typeof candidate === 'string' && candidate.length <= 4096 && candidate.trim().startsWith('{')) {
    const serialized = candidate;
    try { candidate = JSON.parse(serialized); }
    catch { candidate = serialized.match(/(?:^|[,{])\s*['"]url['"]\s*:\s*(['"])([^'"]+)\1\s*(?:[,}]|$)/)?.[2]; }
  }
  if (candidate && typeof candidate === 'object' && 'url' in candidate) candidate = candidate.url;
  if (typeof candidate !== 'string' || candidate.length > 4096 || candidate.includes('\\') || [...candidate].some(c => c.charCodeAt(0) < 32)) return null;
  const target = candidate.trim();
  try {
    const url = new URL(target);
    const official = ['secop.gov.co', 'contratos.gov.co'].some(domain => url.hostname === domain || url.hostname.endsWith(`.${domain}`));
    return official && url.protocol === 'https:' && !url.username && !url.password && (!url.port || url.port === '443') ? target : null;
  } catch { return null; }
}
