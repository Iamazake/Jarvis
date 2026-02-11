/**
 * JARVIS shared DB helpers - conversation_events e autopilot_summaries
 * Usado pela API (mysql2 obrigatório). WhatsApp usa próprio pool opcional.
 */

import mysql from 'mysql2/promise';

let pool = null;
const MYSQL_ENABLED = !!(process.env.MYSQL_HOST && process.env.MYSQL_DATABASE);

export function normalizeJid(jid) {
  if (!jid || typeof jid !== 'string' || !jid.includes('@')) return '';
  let raw = String(jid).trim().toLowerCase();
  if (raw.endsWith('@lid') && raw.includes(':')) {
    const number = raw.split(':')[0].replace(/^\+/, '');
    if (/^\d+$/.test(number)) raw = number + '@s.whatsapp.net';
  }
  return raw;
}

export function getPool() {
  if (!MYSQL_ENABLED) return null;
  if (pool) return pool;
  try {
    pool = mysql.createPool({
      host: process.env.MYSQL_HOST || '127.0.0.1',
      port: Number(process.env.MYSQL_PORT || 3306),
      user: process.env.MYSQL_USER || 'root',
      password: process.env.MYSQL_PASSWORD || '',
      database: process.env.MYSQL_DATABASE || 'jarvis_db',
      waitForConnections: true,
      connectionLimit: 10,
      queueLimit: 0
    });
    return pool;
  } catch (e) {
    return null;
  }
}

/**
 * @param {{ jid_normalized: string, message_id: string, direction: 'in'|'out', text: string|null, ts: string|Date, mode: 'autopilot'|'manual'|'system', meta: object|null }}
 */
export async function insertConversationEvent(params, log = () => {}) {
  const p = getPool();
  if (!p) return;
  const { jid_normalized, message_id, direction, text, ts, mode, meta } = params;
  const tsVal = typeof ts === 'string' ? ts : (ts instanceof Date ? ts.toISOString().slice(0, 23).replace('T', ' ') : null);
  const metaJson = meta ? JSON.stringify(meta) : null;
  try {
    await p.execute(
      `INSERT INTO conversation_events (jid_normalized, message_id, direction, text, ts, mode, meta)
       VALUES (?, ?, ?, ?, ?, ?, ?)
       ON DUPLICATE KEY UPDATE text = VALUES(text), mode = VALUES(mode), meta = VALUES(meta), ts = VALUES(ts)`,
      [jid_normalized, message_id, direction, (text || '').slice(0, 65535), tsVal, mode, metaJson]
    );
    log({ event: 'event_saved', jid: jid_normalized, message_id, direction, mode });
  } catch (err) {
    log({ event: 'event_save_failed', jid: jid_normalized, message_id, error: err.message });
  }
}

/**
 * @param {{ jid_normalized: string, period_start: string, period_end: string, last_n?: number }}
 */
export async function fetchAutopilotEventsForSummary(params) {
  const p = getPool();
  if (!p) return [];
  const { jid_normalized, period_start, period_end, last_n } = params;
  try {
    let sql = `SELECT direction, text, ts FROM conversation_events WHERE jid_normalized = ? AND mode = 'autopilot' AND ts >= ? AND ts <= ? ORDER BY ts ASC`;
    const args = [jid_normalized, period_start, period_end];
    if (last_n != null && Number(last_n) > 0) {
      sql += ` LIMIT ${Math.min(Number(last_n), 500)}`;
    }
    const [rows] = await p.execute(sql, args);
    return rows || [];
  } catch (e) {
    return [];
  }
}

/**
 * @param {{ jid_normalized: string, period_start: string, period_end: string, summary_md: string, highlights_json?: object|null }}
 */
export async function saveAutopilotSummary(params) {
  const p = getPool();
  if (!p) return;
  const { jid_normalized, period_start, period_end, summary_md, highlights_json } = params;
  try {
    await p.execute(
      `INSERT INTO autopilot_summaries (jid_normalized, period_start, period_end, summary_md, highlights_json) VALUES (?, ?, ?, ?, ?)`,
      [jid_normalized, period_start, period_end, summary_md, highlights_json ? JSON.stringify(highlights_json) : null]
    );
  } catch (err) {
    // log optional
  }
}
