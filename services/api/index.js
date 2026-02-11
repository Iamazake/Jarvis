/**
 * JARVIS API - Serviços Internos
 * 
 * API Fastify que recebe mensagens do WhatsApp (Baileys)
 * e processa via Python (AI Engine).
 * 
 * Porta: 5000
 */

import Fastify from 'fastify';
import cors from '@fastify/cors';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync, existsSync } from 'fs';
import mysql from 'mysql2/promise';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '..', '..');

// Carregar .env
try {
  const envPath = join(rootDir, '.env');
  const envContent = readFileSync(envPath, 'utf8');
  envContent.split('\n').forEach(line => {
    const match = line.match(/^([^=:#]+)=(.*)$/);
    if (match) {
      const key = match[1].trim();
      const value = match[2].trim().replace(/^["']|["']$/g, '');
      process.env[key] = value;
    }
  });
  console.log('✅ Variáveis de ambiente carregadas');
} catch (err) {
  console.warn('⚠️ Não foi possível carregar .env:', err.message);
}

const fastify = Fastify({
  logger: {
    level: 'info',
    transport: {
      target: 'pino-pretty',
      options: {
        colorize: true
      }
    }
  }
});

await fastify.register(cors, {
  origin: true
});

// ================================
// Estado Global
// ================================
const state = {
  messageQueue: [],
  processing: false,
  stats: {
    received: 0,
    processed: 0,
    errors: 0
  }
};

const WEBHOOK_PROCESS_TIMEOUT_MS = Number(process.env.WEBHOOK_PROCESS_TIMEOUT_MS || 22000);
const WEBHOOK_IDEMPOTENCY_TTL_MS = Number(process.env.WEBHOOK_IDEMPOTENCY_TTL_MS || 300000);
const WEBHOOK_IDEMPOTENCY_MAX = Number(process.env.WEBHOOK_IDEMPOTENCY_MAX || 1000);
const webhookResultCache = new Map();
const webhookInFlight = new Set();

// ================================
// Fila + Worker (ACK burro, dedupe apenas)
// ================================
const API_QUEUE_ENABLED = ['1', 'true', 'yes'].includes(String(process.env.API_QUEUE_ENABLED || '1').trim().toLowerCase());
const API_QUEUE_MAX_SIZE = Math.max(1, Number(process.env.API_QUEUE_MAX_SIZE || 1000));
const API_QUEUE_DEDUPE_TTL_MS = Number(process.env.API_QUEUE_DEDUPE_TTL_MS || 600000); // 10 min
const API_QUEUE_CONCURRENCY = Math.max(1, Number(process.env.API_QUEUE_CONCURRENCY || 3));
const API_WHATSAPP_SERVICE_URL = (process.env.API_WHATSAPP_SERVICE_URL || 'http://127.0.0.1:3001').replace(/\/$/, '');
const WHATSAPP_SEND_TIMEOUT_MS = Number(process.env.WHATSAPP_SEND_TIMEOUT_MS || 8000);

// JARVIS data dir (context_state.json) - mesmo path que Python
const JARVIS_DATA_DIR = process.env.JARVIS_DATA_DIR ? process.env.JARVIS_DATA_DIR.trim() : join(rootDir, 'data');
const CONTEXT_STATE_PATH = join(JARVIS_DATA_DIR, 'context_state.json');

// MySQL pool (conversation_events outbound + autopilot_summaries)
let mysqlPool = null;
const MYSQL_ENABLED = !!(process.env.MYSQL_HOST && process.env.MYSQL_DATABASE);
if (MYSQL_ENABLED) {
  try {
    mysqlPool = mysql.createPool({
      host: process.env.MYSQL_HOST || '127.0.0.1',
      port: Number(process.env.MYSQL_PORT || 3306),
      user: process.env.MYSQL_USER || 'root',
      password: process.env.MYSQL_PASSWORD || '',
      database: process.env.MYSQL_DATABASE || 'jarvis_db',
      waitForConnections: true,
      connectionLimit: 10,
      queueLimit: 0
    });
  } catch (e) {
    console.warn('MySQL pool não inicializado:', e.message);
  }
}

function normalizeJid(jid) {
  if (!jid || typeof jid !== 'string' || !jid.includes('@')) return '';
  let raw = jid.trim().toLowerCase();
  if (raw.endsWith('@lid') && raw.includes(':')) {
    const number = raw.split(':')[0].replace(/^\+/, '');
    if (/^\d+$/.test(number)) raw = number + '@s.whatsapp.net';
  }
  return raw;
}

function getAutopilotStatusFromContextState(jid) {
  const normalized = normalizeJid(jid);
  if (!normalized) return { enabled: false };
  if (!existsSync(CONTEXT_STATE_PATH)) return { enabled: false };
  try {
    const data = JSON.parse(readFileSync(CONTEXT_STATE_PATH, 'utf8'));
    const autopilot = data.autopilot_contacts || {};
    const now = new Date().toISOString();
    for (const [key, entry] of Object.entries(autopilot)) {
      if (!entry.enabled) continue;
      const keyNorm = key.includes('@') ? normalizeJid(key) : key.toLowerCase();
      if (keyNorm === normalized) {
        const expires = entry.expires_at;
        if (expires && new Date(expires).toISOString() < now) continue;
        return { enabled: true };
      }
    }
    const alias = data.autopilot_alias || {};
    for (const [nameKey, storedJid] of Object.entries(alias)) {
      if (normalizeJid(storedJid) === normalized) return { enabled: true };
    }
  } catch (e) {
    // ignore
  }
  return { enabled: false };
}

async function insertConversationEventOutbound(jidNormalized, messageId, text, mode) {
  if (!mysqlPool) return;
  const ts = new Date();
  const mid = messageId || `out-${ts.getTime()}-${Math.random().toString(36).slice(2, 9)}`;
  try {
    await mysqlPool.execute(
      `INSERT INTO conversation_events (jid_normalized, message_id, direction, text, ts, mode, meta)
       VALUES (?, ?, 'out', ?, ?, ?, NULL)
       ON DUPLICATE KEY UPDATE text = VALUES(text), mode = VALUES(mode), ts = VALUES(ts)`,
      [jidNormalized, mid, (text || '').slice(0, 65535), ts, mode || 'autopilot']
    );
    fastify.log.info({ msg: 'conversation_event saved', jid: jidNormalized, message_id: mid, direction: 'out', mode: mode || 'autopilot' });
  } catch (err) {
    fastify.log.warn({ msg: 'conversation_event insert failed', jid: jidNormalized, error: err.message });
  }
}

function getAdminJid() {
  const admin = (process.env.JARVIS_ADMIN_JID || '').trim();
  if (admin && admin.includes('@')) return normalizeJid(admin);
  const owner = (process.env.JARVIS_OWNER_NUMBER || '').trim().replace(/\D/g, '');
  if (owner) return owner + '@s.whatsapp.net';
  return null;
}

function isInternalRequest(request) {
  const ip = request.ip || request.headers['x-forwarded-for'] || '';
  const isLocal = ip === '127.0.0.1' || ip === '::1' || ip === '::ffff:127.0.0.1' || String(ip).startsWith('127.') || String(ip).startsWith('::1');
  const internalSecret = process.env.JARVIS_INTERNAL_SECRET || '';
  const hasInternalHeader = internalSecret && request.headers['x-jarvis-internal'] === internalSecret;
  return isLocal || hasInternalHeader;
}

async function fetchEventsForSummary(jidNormalized, periodStart, periodEnd, limitN = null) {
  if (!mysqlPool) return [];
  try {
    const limit = limitN != null && Number.isInteger(limitN) && limitN > 0 ? Math.min(limitN, 500) : null;
    const order = limit ? 'DESC' : 'ASC';
    let sql = `SELECT direction, text, ts FROM conversation_events WHERE jid_normalized = ? AND mode = 'autopilot' AND ts >= ? AND ts <= ? ORDER BY ts ${order}`;
    if (limit) sql += ` LIMIT ${limit}`;
    const [rows] = await mysqlPool.execute(sql, [jidNormalized, periodStart, periodEnd]);
    const list = rows || [];
    return limit ? list.reverse() : list;
  } catch (e) {
    fastify.log.warn({ msg: 'fetchEventsForSummary failed', jid: jidNormalized, error: e.message });
    return [];
  }
}

function buildSummaryFromEvents(events) {
  const inMsgs = events.filter(r => r.direction === 'in').map(r => (r.text || '').trim()).filter(Boolean);
  const outMsgs = events.filter(r => r.direction === 'out').map(r => (r.text || '').trim()).filter(Boolean);
  const topics = [...inMsgs.slice(-5), ...outMsgs.slice(-5)].filter(Boolean).slice(0, 10);
  let md = `**Contexto:** Conversa com ${inMsgs.length} mensagem(ns) recebida(s) e ${outMsgs.length} resposta(s) do autopilot.\n\n`;
  md += `**Tópicos (últimas trocas):**\n`;
  topics.forEach(t => { md += `- ${t.slice(0, 120)}${t.length > 120 ? '...' : ''}\n`; });
  md += `\n**Pendências:**\n- (Nenhuma identificada automaticamente)\n`;
  return md;
}

async function saveAutopilotSummary(jidNormalized, periodStart, periodEnd, summaryMd, highlightsJson = null) {
  if (!mysqlPool) return;
  try {
    await mysqlPool.execute(
      `INSERT INTO autopilot_summaries (jid_normalized, period_start, period_end, summary_md, highlights_json) VALUES (?, ?, ?, ?, ?)`,
      [jidNormalized, periodStart, periodEnd, summaryMd, highlightsJson ? JSON.stringify(highlightsJson) : null]
    );
    fastify.log.info({ msg: 'autopilot_summary saved', jid: jidNormalized, period_end: periodEnd });
  } catch (err) {
    fastify.log.warn({ msg: 'autopilot_summary insert failed', jid: jidNormalized, error: err.message });
  }
}

const jobQueue = [];
const seenMessageIds = new Map(); // message_id -> timestamp (para dedupe do ACK)
const queueInFlightMessageIds = new Set(); // worker já pegou o job
let queueActiveGlobal = 0;
const queueActiveByJid = new Set();

function extractTimingLines(stderrText = '') {
  return String(stderrText)
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.startsWith('[timing]'));
}

function tailText(text = '', limit = 500) {
  const content = String(text || '').trim();
  if (!content) return '';
  if (content.length <= limit) return content;
  return content.slice(-limit);
}

// ================================
// Funções Utilitárias
// ================================

/**
 * Executa comando Python para processar mensagem via JARVIS (run_jarvis_message.py).
 * Usa JID (from_jid) para decisão de autopilot; display_name só para exibição.
 */
async function processPythonAI(message, jid, displayName, timeoutMs = WEBHOOK_PROCESS_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const pythonScript = join(rootDir, 'run_jarvis_message.py');
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

    const args = [pythonScript, '--message', message];
    if (jid && String(jid).includes('@')) {
      args.push('--jid', String(jid));
    }
    args.push('--sender', displayName || jid || 'user');

    const python = spawn(pythonCmd, args, {
      cwd: rootDir,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', JARVIS_DATA_DIR }
    });

    let stdout = '';
    let stderr = '';
    let done = false;

    const timeout = setTimeout(() => {
      if (done) return;
      done = true;
      try { python.kill(); } catch {}
      const timing = extractTimingLines(stderr).slice(-6).join(' | ');
      const suffix = timing ? ` | timing=${timing}` : '';
      reject(new Error(`Python timeout após ${timeoutMs}ms${suffix}`));
    }, timeoutMs);

    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', (code) => {
      if (done) return;
      done = true;
      clearTimeout(timeout);
      const timing = extractTimingLines(stderr);
      // Robustez: parse apenas a PRIMEIRA linha JSON válida do stdout
      // (ignora linhas de log acidentais que possam ter ido pro stdout)
      if (code === 0) {
        const lines = stdout.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
        let parsed = null;
        for (const line of lines) {
          if (!line.startsWith('{')) continue;
          try {
            parsed = JSON.parse(line);
            break;
          } catch { /* não é JSON, tentar próxima */ }
        }
        if (parsed) {
          resolve({ ...parsed, __timing: timing });
        } else if (stdout.trim()) {
          // Fallback: se nenhuma linha era JSON, retorna como texto
          resolve({ response: stdout.trim(), cached: false, __timing: timing });
        } else {
          resolve({ action: 'ignore', response: '', reason: 'empty_stdout', __timing: timing });
        }
      } else {
        reject(new Error(tailText(stderr) || `Python exited with code ${code}`));
      }
    });

    python.on('error', (err) => {
      if (done) return;
      done = true;
      clearTimeout(timeout);
      reject(err);
    });
  });
}

function cleanupWebhookCache(now = Date.now()) {
  for (const [key, entry] of webhookResultCache.entries()) {
    if ((now - entry.createdAt) > WEBHOOK_IDEMPOTENCY_TTL_MS) {
      webhookResultCache.delete(key);
    }
  }
  while (webhookResultCache.size > WEBHOOK_IDEMPOTENCY_MAX) {
    const oldestKey = webhookResultCache.keys().next().value;
    if (!oldestKey) break;
    webhookResultCache.delete(oldestKey);
  }
}

function cleanupSeenMessageIds(now = Date.now()) {
  for (const [key, ts] of seenMessageIds.entries()) {
    if ((now - ts) > API_QUEUE_DEDUPE_TTL_MS) {
      seenMessageIds.delete(key);
    }
  }
}

function isConnectionError(err) {
  const code = err?.code || '';
  const message = String(err?.message || '').toLowerCase();
  return ['ECONNREFUSED', 'ENOTFOUND', 'EAI_AGAIN', 'ECONNRESET'].includes(code) || message.includes('econnrefused') || message.includes('enotfound') || message.includes('eai_again');
}

/**
 * @param {string} jid
 * @param {string} message
 * @param {{ mode?: string, job_id?: string, reply_to_message_id?: string }} [opts]
 * @returns {Promise<{ ok: boolean, message_id?: string }>}
 */
async function sendToWhatsApp(jid, message, opts = {}) {
  const url = `${API_WHATSAPP_SERVICE_URL}/send`;
  const timeoutMs = WHATSAPP_SEND_TIMEOUT_MS;
  const body = JSON.stringify({
    to: jid,
    message,
    mode: opts.mode || undefined,
    job_id: opts.job_id || undefined,
    reply_to_message_id: opts.reply_to_message_id || undefined
  });
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    const text = await res.text().catch(() => '');
    if (!res.ok) throw new Error(`HTTP ${res.status} ${text.slice(0, 80)}`);
    let data = {};
    if (text) try { data = JSON.parse(text); } catch (_) {}
    return { ok: true, message_id: data.message_id };
  } catch (err) {
    clearTimeout(timeoutId);
    throw err;
  }
}

/**
 * Policy layer: perguntas sobre status/biografia de pessoa real → resposta fixa (sem alucinação).
 * Retorna { action: 'reply', response } se aplicar; null para seguir para o LLM.
 */
function policyStatusOrBioQuestion(message) {
  const t = (message || '').toLowerCase().trim();
  const statusBioPatterns = [
    /\b(está|ta)\s+(ocupado|livre|disponível|online|offline)\b/,
    /\b(status|biografia|bio)\s+(de|do|da)\s+\w+/,
    /\w+\s+está\s+(ocupado|livre|disponível)/,
    /\b(como|onde)\s+(está|tá)\s+\w+\b/,
    /\b(está\s+ocupado|está\s+livre)\s*\??\s*$/
  ];
  if (statusBioPatterns.some(r => r.test(t))) {
    return {
      action: 'reply',
      response: 'Eu não tenho status em tempo real. Posso mandar uma mensagem perguntando. Quer que eu envie?',
      reason: 'policy_status_question'
    };
  }
  return null;
}

/**
 * Resposta rápida sem IA (comandos básicos)
 */
function quickResponse(message) {
  const lower = message.toLowerCase().trim();
  
  const quickReplies = {
    'ping': { response: 'Pong! 🏓', cached: true },
    'oi': { response: 'Olá! 👋 Como posso ajudar?', cached: true },
    'olá': { response: 'Olá! 👋 Como posso ajudar?', cached: true },
    'status': { response: `🤖 JARVIS Online!\n📊 Msgs recebidas: ${state.stats.received}\n✅ Processadas: ${state.stats.processed}`, cached: true },
    'ajuda': { response: '📚 Comandos:\n• ping - Testar conexão\n• status - Ver estatísticas\n• Qualquer pergunta - Respondo com IA!', cached: true }
  };

  return quickReplies[lower] || null;
}

// ================================
// Rotas da API
// ================================

/**
 * Health Check
 */
fastify.get('/health', async (request, reply) => {
  return {
    status: 'healthy',
    service: 'jarvis-api',
    uptime: process.uptime(),
    stats: state.stats
  };
});

/**
 * Estatísticas
 */
fastify.get('/stats', async (request, reply) => {
  return {
    ...state.stats,
    queueSize: state.messageQueue.length,
    processing: state.processing,
    jobQueueLength: jobQueue.length,
    queueActiveGlobal,
    queueInFlightCount: queueInFlightMessageIds.size,
    apiQueueEnabled: API_QUEUE_ENABLED
  };
});

/**
 * GET /internal/autopilot-status?jid=xxx - Lê context_state.json e retorna se autopilot está ON para o JID.
 * Uso: WhatsApp service antes de gravar inbound. Apenas localhost.
 */
fastify.get('/internal/autopilot-status', async (request, reply) => {
  if (!isInternalRequest(request)) return reply.status(403).send({ error: 'Forbidden' });
  const jid = (request.query && request.query.jid) || '';
  const { enabled } = getAutopilotStatusFromContextState(jid);
  return { enabled };
});

/**
 * POST /internal/autopilot-summary - Gera e persiste resumo (com checagem de privacidade).
 * Requester via header X-Jarvis-Requester-Jid (não confiar no body).
 * Body: { target_jid, period?: 'hoje'|'24h', last_n?: number }.
 */
fastify.post('/internal/autopilot-summary', async (request, reply) => {
  if (!isInternalRequest(request)) return reply.status(403).send({ error: 'Forbidden' });
  const requesterRaw = (request.headers && (request.headers['x-jarvis-requester-jid'] || request.headers['X-Jarvis-Requester-Jid'])) || '';
  const requester = normalizeJid(requesterRaw);
  const { target_jid, period = '24h', last_n } = request.body || {};
  const target = normalizeJid(target_jid || '');
  if (!target) return reply.status(400).send({ error: 'target_jid obrigatório' });
  const adminJid = getAdminJid();
  const allowed = (adminJid && requester === adminJid) || requester === target;
  if (!allowed) {
    return reply.status(403).send({
      allowed: false,
      message: 'Acesso negado: você só pode pedir resumo do seu próprio chat.'
    });
  }
  const now = new Date();
  let periodStart, periodEnd;
  if (last_n != null && Number(last_n) > 0) {
    periodEnd = now.toISOString().slice(0, 19).replace('T', ' ');
    periodStart = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 19).replace('T', ' ');
  } else if (period === 'hoje') {
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    periodStart = start.toISOString().slice(0, 19).replace('T', ' ');
    periodEnd = now.toISOString().slice(0, 19).replace('T', ' ');
  } else {
    const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    periodStart = start.toISOString().slice(0, 19).replace('T', ' ');
    periodEnd = now.toISOString().slice(0, 19).replace('T', ' ');
  }
  const events = await fetchEventsForSummary(target, periodStart, periodEnd, last_n != null ? Number(last_n) : null);
  const summaryMd = events.length === 0
    ? 'Sem eventos de autopilot no período informado.'
    : buildSummaryFromEvents(events);
  if (events.length > 0) await saveAutopilotSummary(target, periodStart, periodEnd, summaryMd);
  return { allowed: true, summary_md: summaryMd };
});

/**
 * POST /internal/generate-autopilot-summary - Gera resumo ao desativar autopilot (sem checagem de privacidade).
 * Body: { jid, period_start, period_end } (ISO ou YYYY-MM-DD HH:mm:ss).
 */
fastify.post('/internal/generate-autopilot-summary', async (request, reply) => {
  if (!isInternalRequest(request)) return reply.status(403).send({ error: 'Forbidden' });
  const { jid, period_start, period_end } = request.body || {};
  const jidNorm = normalizeJid(jid || '');
  if (!jidNorm || !period_start || !period_end) {
    return reply.status(400).send({ error: 'jid, period_start e period_end obrigatórios' });
  }
  const periodStart = String(period_start).slice(0, 19).replace('T', ' ');
  const periodEnd = String(period_end).slice(0, 19).replace('T', ' ');
  const events = await fetchEventsForSummary(jidNorm, periodStart, periodEnd);
  const summaryMd = events.length === 0
    ? 'Sem eventos de autopilot no período informado.'
    : buildSummaryFromEvents(events);
  if (events.length > 0) await saveAutopilotSummary(jidNorm, periodStart, periodEnd, summaryMd);
  return { summary_md: summaryMd };
});

/**
 * Webhook - Recebe mensagens do WhatsApp (Baileys)
 */
fastify.post('/webhook', async (request, reply) => {
  const { sender, message, timestamp, pushName, from_jid, display_name, message_id } = request.body;
  const jid = from_jid || sender;
  const displayName = display_name || pushName || '';
  const messageId = message_id || '';

  if (!message || !jid) {
    return reply.status(400).send({ error: 'sender/from_jid e message são obrigatórios' });
  }

  cleanupWebhookCache();
  if (messageId) {
    const cached = webhookResultCache.get(messageId);
    if (cached) {
      fastify.log.info({ msg: 'Webhook duplicado (cache hit)', messageId, jid });
      return cached.result;
    }
    if (webhookInFlight.has(messageId)) {
      fastify.log.warn({ msg: 'Webhook duplicado (in-flight)', messageId, jid });
      return {
        success: true,
        action: 'ignore',
        response: '',
        sender,
        reason: 'duplicate_inflight'
      };
    }
  }

  state.stats.received++;
  const startedAt = Date.now();

  fastify.log.info({
    msg: 'Mensagem recebida',
    messageId: messageId || '(sem message_id)',
    jid,
    displayName: displayName || '(sem nome)',
    message: message.substring(0, 100)
  });

  if (messageId) {
    webhookInFlight.add(messageId);
  }

  try {
    const policyResult = policyStatusOrBioQuestion(message);
    if (policyResult) {
      state.stats.processed++;
      const payload = { success: true, action: 'reply', response: policyResult.response, reason: policyResult.reason };
      if (messageId) webhookResultCache.set(messageId, { createdAt: Date.now(), result: payload });
      return payload;
    }
    fastify.log.info({ msg: 'ANTES processPythonAI', messageId: messageId || '(sem message_id)', jid });
    const result = await processPythonAI(message, jid, displayName, WEBHOOK_PROCESS_TIMEOUT_MS);
    const pythonTiming = Array.isArray(result?.__timing) ? result.__timing : [];
    const elapsedMs = Date.now() - startedAt;
    fastify.log.info({ msg: 'DEPOIS processPythonAI', messageId: messageId || '(sem message_id)', jid, elapsedMs });
    if (pythonTiming.length > 0) {
      fastify.log.info({
        msg: 'Python timing',
        messageId: messageId || '(sem message_id)',
        steps: pythonTiming.slice(-10)
      });
    }

    state.stats.processed++;

    const payload = {
      success: true,
      action: result.action || 'reply',
      response: result.response ?? '',
      cached: result.cached || false,
      sender,
      reason: result.reason
    };
    if (messageId) {
      webhookResultCache.set(messageId, { createdAt: Date.now(), result: payload });
    }
    return payload;

  } catch (error) {
    state.stats.errors++;
    fastify.log.error({ msg: 'Erro ao processar', messageId: messageId || '(sem message_id)', error: error.message });

    // Não enviar mensagem genérica (evita "Olá" ou greeting em caso de fetch/erro)
    const payload = {
      success: false,
      action: 'ignore',
      response: '',
      reason: error.message?.includes('timeout') ? 'timeout' : 'error',
      error: error.message
    };
    if (messageId) {
      webhookResultCache.set(messageId, { createdAt: Date.now(), result: payload });
    }
    return payload;
  } finally {
    if (messageId) {
      webhookInFlight.delete(messageId);
    }
  }
});

/**
 * POST /queue - Enfileirar mensagem (ACK burro: só dedupe, não consulta resultado).
 * Worker processa em background e chama POST /send do WhatsApp.
 */
fastify.post('/queue', async (request, reply) => {
  if (!API_QUEUE_ENABLED) {
    return reply.status(404).send({ error: 'Queue disabled', success: false });
  }
  const { sender, message, timestamp, pushName, from_jid, display_name, message_id } = request.body || {};
  const jid = (from_jid || sender || '').toString().trim();
  const displayName = (display_name || pushName || '').toString().trim();
  const msgId = (message_id || '').toString().trim();

  if (!message || !jid) {
    return reply.status(400).send({ error: 'message e jid (ou from_jid/sender) são obrigatórios', success: false });
  }

  cleanupSeenMessageIds();

  if (msgId) {
    if (queueInFlightMessageIds.has(msgId)) {
      return { success: true, status: 'duplicate_inflight', message_id: msgId };
    }
    const seenAt = seenMessageIds.get(msgId);
    if (seenAt != null && (Date.now() - seenAt) < API_QUEUE_DEDUPE_TTL_MS) {
      return { success: true, status: 'duplicate_seen', message_id: msgId };
    }
  }

  if (jobQueue.length >= API_QUEUE_MAX_SIZE) {
    return reply.status(503).send({ success: false, status: 'queue_full', message_id: msgId || null });
  }

  const job = {
    message_id: msgId,
    jid,
    displayName: displayName || jid,
    message: String(message),
    sender: (sender || jid).toString(),
    timestamp: timestamp || Date.now(),
    from_jid: jid,
    pushName: displayName
  };
  jobQueue.push(job);
  state.stats.received++;

  setImmediate(() => pump());
  return { success: true, status: 'enqueued', message_id: msgId || null };
});

function pump() {
  if (!API_QUEUE_ENABLED || queueActiveGlobal >= API_QUEUE_CONCURRENCY || jobQueue.length === 0) return;
  let idx = -1;
  for (let i = 0; i < jobQueue.length; i++) {
    if (!queueActiveByJid.has(jobQueue[i].jid)) {
      idx = i;
      break;
    }
  }
  if (idx === -1) return;
  const job = jobQueue.splice(idx, 1)[0];
  queueActiveGlobal++;
  queueActiveByJid.add(job.jid);

  processOneJob(job).finally(() => {
    queueActiveGlobal--;
    queueActiveByJid.delete(job.jid);
    pump();
  });
}

async function processOneJob(job) {
  const { message_id: msgId, jid, displayName, message } = job;
  const startAt = Date.now();
  if (msgId) queueInFlightMessageIds.add(msgId);
  fastify.log.info({ msg: 'queue job start', message_id: msgId || '(sem id)', jid });

  try {
    const policyResult = policyStatusOrBioQuestion(message);
    let result;
    if (policyResult) {
      result = { action: 'reply', response: policyResult.response, reason: policyResult.reason };
      fastify.log.info({ msg: 'policy_status_question', message_id: msgId || '(sem id)', jid });
    } else {
      fastify.log.info({ msg: 'python_start', message_id: msgId || '(sem id)', jid });
      result = await processPythonAI(message, jid, displayName, WEBHOOK_PROCESS_TIMEOUT_MS);
      fastify.log.info({ msg: 'python_end', message_id: msgId || '(sem id)', jid, elapsedMs: Date.now() - startAt, reason: result?.reason });
    }

    state.stats.processed++;

    if (result?.action === 'reply' && result?.response) {
      fastify.log.info({ msg: 'send_start', message_id: msgId || '(sem id)', jid });
      let lastErr;
      const outboundMode = result.mode || 'autopilot';
      for (let attempt = 1; attempt <= 2; attempt++) {
        try {
          await sendToWhatsApp(jid, result.response, { mode: outboundMode, job_id: msgId || `job-${Date.now()}`, reply_to_message_id: msgId || undefined });
          fastify.log.info({ msg: 'send_end', message_id: msgId || '(sem id)', jid, elapsedMs: Date.now() - startAt });
          break;
        } catch (err) {
          lastErr = err;
          if (isConnectionError(err) && attempt < 2) {
            await new Promise((r) => setTimeout(r, 300));
            continue;
          }
          fastify.log.error({ msg: 'send_failed', message_id: msgId || '(sem id)', jid, error: err.message });
          break;
        }
      }
      if (lastErr && !isConnectionError(lastErr)) {
        fastify.log.error({ msg: 'send_not_retried', message_id: msgId || '(sem id)', jid, error: lastErr.message });
      }
    } else {
      fastify.log.info({ msg: 'queue job ignore', message_id: msgId || '(sem id)', jid, reason: result?.reason || 'no_response', elapsedMs: Date.now() - startAt });
    }
  } catch (err) {
    state.stats.errors++;
    const elapsedMs = Date.now() - startAt;
    fastify.log.error({ msg: 'queue job error', message_id: msgId || '(sem id)', jid, error: err.message, elapsedMs });
  } finally {
    if (msgId) {
      queueInFlightMessageIds.delete(msgId);
      seenMessageIds.set(msgId, Date.now());
    }
    fastify.log.info({ msg: 'queue job done', message_id: msgId || '(sem id)', jid, elapsedMs: Date.now() - startAt });
  }
}

/**
 * Processar mensagem diretamente (teste)
 */
fastify.post('/process', async (request, reply) => {
  const { message, sender = 'test' } = request.body;
  
  if (!message) {
    return reply.status(400).send({ error: 'message é obrigatório' });
  }
  
  // Tenta resposta rápida primeiro
  let result = quickResponse(message);
  
  if (result) {
    return {
      success: true,
      response: result.response,
      cached: true
    };
  }

  try {
    // Verifica se é um comando de ação (enviar mensagem)
    const actionResult = await detectAndExecuteAction(message);
    if (actionResult) {
      return actionResult;
    }
    
    // Tenta usar OpenAI diretamente via API
    const openaiKey = process.env.OPENAI_API_KEY;
    
    if (openaiKey && openaiKey !== 'sua_chave_aqui') {
      fastify.log.info({ msg: 'Usando OpenAI diretamente', model: process.env.OPENAI_MODEL || 'gpt-4o-mini' });
      
      try {
        const response = await fetch('https://api.openai.com/v1/chat/completions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${openaiKey}`
          },
          body: JSON.stringify({
            model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
            messages: [
              {
                role: 'system',
                content: `Você é o JARVIS, um assistente virtual inteligente como o do Tony Stark. Você é prestativo, proativo e resolve problemas de forma autônoma.

Quando o usuário pedir para enviar mensagem, responda no formato:
[AÇÃO:ENVIAR]
Para: <nome do contato>
Mensagem: <mensagem a enviar>

Responda sempre de forma concisa e natural em português brasileiro.`
              },
              {
                role: 'user',
                content: message
              }
            ],
            temperature: 0.7,
            max_tokens: 500
          })
        });

        if (response.ok) {
          const data = await response.json();
          let aiResponse = data.choices[0]?.message?.content || 'Desculpe, não consegui gerar uma resposta.';
          
          // Verifica se a IA retornou uma ação
          if (aiResponse.includes('[AÇÃO:ENVIAR]')) {
            const actionResult = await parseAndExecuteAIAction(aiResponse);
            if (actionResult) {
              return actionResult;
            }
          }
          
          return {
            success: true,
            response: aiResponse,
            cached: false,
            provider: 'openai-direct'
          };
        } else {
          fastify.log.error({ msg: 'Erro na API OpenAI', status: response.status });
        }
      } catch (openaiError) {
        fastify.log.error({ msg: 'Erro ao chamar OpenAI', error: openaiError.message });
      }
    } else {
      fastify.log.warn('OPENAI_API_KEY não configurada');
    }

    // Fallback: resposta padrão
    return { 
      success: true, 
      response: 'Olá! Sou o JARVIS. Como posso ajudar?',
      cached: false,
      provider: 'fallback'
    };
    
  } catch (error) {
    fastify.log.error({ msg: 'Erro no /process', error: error.message });
    return reply.status(500).send({ 
      success: false, 
      error: error.message,
      response: 'Desculpe, estou com dificuldades técnicas no momento.'
    });
  }
});

/**
 * Gerar mensagem com IA (SEM executar ações)
 * Usado pelo CLI para apenas gerar texto
 */
fastify.post('/generate', async (request, reply) => {
  const { prompt, context = '' } = request.body;
  
  if (!prompt) {
    return reply.status(400).send({ error: 'prompt é obrigatório' });
  }
  
  const openaiKey = process.env.OPENAI_API_KEY;
  
  if (!openaiKey || openaiKey === 'sua_chave_aqui') {
    return { 
      success: false, 
      response: 'API de IA não configurada',
      provider: 'none'
    };
  }
  
  try {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${openaiKey}`
      },
      body: JSON.stringify({
        model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: `Você é o JARVIS, assistente virtual. Escreva APENAS a mensagem solicitada, sem explicações, sem aspas, sem "Mensagem:" no início. Seja natural e amigável. ${context}`
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.8,
        max_tokens: 300
      })
    });

    if (response.ok) {
      const data = await response.json();
      const aiResponse = data.choices[0]?.message?.content || '';
      
      return {
        success: true,
        response: aiResponse.trim(),
        provider: 'openai'
      };
    } else {
      fastify.log.error({ msg: 'Erro na API OpenAI', status: response.status });
      return { success: false, response: 'Erro ao gerar mensagem', provider: 'error' };
    }
  } catch (error) {
    fastify.log.error({ msg: 'Erro no /generate', error: error.message });
    return { success: false, response: 'Erro ao conectar com IA', provider: 'error' };
  }
});

/**
 * Detecta e executa ações diretas (enviar mensagem, etc)
 */
async function detectAndExecuteAction(message) {
  const lower = message.toLowerCase();
  
  // Padrões de comando de envio
  const sendPatterns = [
    // "manda mensagem para X dizendo Y"
    /(?:manda|envia|envi[ae]|mande)\s+(?:uma?\s+)?(?:mensagem|msg)?\s*(?:para?|pro?|a)\s+(.+?)(?:\s+(?:dizendo|falando|com|escrevendo)\s+(.+))?$/i,
    // "fala para X que Y"
    /(?:fala|diz|avisa)\s+(?:para?|pro?|a)\s+(.+?)\s+(?:que\s+)?(.+)$/i,
    // "pergunta para X Y"
    /(?:pergunta|pergunte)\s+(?:para?|pro?|a)\s+(.+?)\s+(.+)$/i,
    // "manda uma mensagem carinhosa/de bom dia para X"
    /(?:manda|envia)\s+(?:uma?\s+)?(?:mensagem\s+)?(carinhosa|de\s+bom\s+dia|de\s+boa\s+noite|rom[aâ]ntica|fofa|de\s+amor)\s+(?:para?|pro?|a)\s+(.+)$/i
  ];
  
  for (let i = 0; i < sendPatterns.length; i++) {
    const pattern = sendPatterns[i];
    const match = message.match(pattern);
    if (match) {
      let contactName, msgContent, msgIntent;
      
      // Último padrão é especial (mensagem carinhosa para X)
      if (i === 3) {
        msgIntent = match[1]?.trim();
        contactName = match[2]?.trim();
        msgContent = null;
      } else {
        contactName = match[1]?.trim();
        msgContent = match[2]?.trim();
      }
      
      if (contactName) {
        // Busca o contato
        try {
          const searchResp = await fetch(`http://localhost:3001/contacts/search?q=${encodeURIComponent(contactName)}`);
          const searchData = await searchResp.json();
          
          if (searchData.success && searchData.contact) {
            // Se não tem mensagem específica, gera uma com IA
            if (!msgContent) {
              const intent = msgIntent || 'saudação amigável';
              msgContent = await generateMessage(contactName, intent);
            }
            
            // Envia a mensagem
            const sendResp = await fetch('http://localhost:3001/send-by-name', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name: contactName, message: msgContent })
            });
            const sendData = await sendResp.json();
            
            if (sendData.success) {
              return {
                success: true,
                response: `✅ Mensagem enviada para ${sendData.sentTo}!\n\n📤 "${msgContent}"`,
                action: 'send',
                cached: false
              };
            } else {
              return {
                success: true,
                response: `❌ Não consegui enviar para ${contactName}: ${sendData.error || 'erro desconhecido'}`,
                action: 'send_failed',
                cached: false
              };
            }
          } else {
            return {
              success: true,
              response: `🔍 Não encontrei o contato "${contactName}". Tente adicionar primeiro ou verificar o nome.`,
              action: 'contact_not_found',
              cached: false
            };
          }
        } catch (err) {
          fastify.log.error({ msg: 'Erro ao executar ação', error: err.message });
        }
      }
    }
  }
  
  return null; // Não é uma ação direta
}

/**
 * Parse e executa ação da resposta da IA
 */
async function parseAndExecuteAIAction(aiResponse) {
  const lines = aiResponse.split('\n');
  let contactName = null;
  let msgContent = null;
  
  for (const line of lines) {
    if (line.startsWith('Para:')) {
      contactName = line.replace('Para:', '').trim();
    }
    if (line.startsWith('Mensagem:')) {
      msgContent = line.replace('Mensagem:', '').trim();
    }
  }
  
  if (contactName && msgContent) {
    try {
      const sendResp = await fetch('http://localhost:3001/send-by-name', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: contactName, message: msgContent })
      });
      const sendData = await sendResp.json();
      
      if (sendData.success) {
        return {
          success: true,
          response: `✅ Mensagem enviada para ${sendData.sentTo}!\n\n📤 "${msgContent}"`,
          action: 'send',
          cached: false
        };
      }
    } catch (err) {
      fastify.log.error({ msg: 'Erro ao executar ação da IA', error: err.message });
    }
  }
  
  return null;
}

/**
 * Gera uma mensagem usando IA
 */
async function generateMessage(contactName, intent) {
  const openaiKey = process.env.OPENAI_API_KEY;
  
  if (!openaiKey) {
    return `Olá! Como você está?`;
  }
  
  try {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${openaiKey}`
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: 'Escreva apenas a mensagem, sem explicações. Seja natural e amigável.'
          },
          {
            role: 'user',
            content: `Escreva uma mensagem de ${intent} para ${contactName}. Curta e natural.`
          }
        ],
        temperature: 0.8,
        max_tokens: 100
      })
    });
    
    if (response.ok) {
      const data = await response.json();
      return data.choices[0]?.message?.content || `Olá ${contactName}! Como vai?`;
    }
  } catch (err) {
    fastify.log.error({ msg: 'Erro ao gerar mensagem', error: err.message });
  }
  
  return `Olá ${contactName}! Como vai?`;
}

/**
 * Enviar mensagem via WhatsApp (proxy para Baileys)
 */
fastify.post('/send', async (request, reply) => {
  const { to, message } = request.body;
  
  if (!to || !message) {
    return reply.status(400).send({ error: 'to e message são obrigatórios' });
  }

  try {
    // Envia para o serviço Baileys
    const response = await fetch('http://localhost:3001/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ to, message })
    });

    const result = await response.json();
    return result;
  } catch (error) {
    return reply.status(500).send({ 
      success: false, 
      error: 'Serviço WhatsApp não disponível' 
    });
  }
});

/**
 * Receber notificação de mídia do Baileys
 * Encaminha para Python (MediaMonitor)
 */
fastify.post('/media', async (request, reply) => {
  const { sender, pushName, mediaType, mimetype, caption, timestamp } = request.body;
  
  fastify.log.info({
    msg: 'Mídia recebida',
    sender,
    pushName,
    mediaType
  });

  // Aqui podemos processar a mídia ou notificar o Python
  // Por ora, apenas logamos (o Python processa via handlers)
  
  return { success: true, mediaType };
});

/**
 * Receber notificação de presença do Baileys
 * Encaminha para Python (PresenceMonitor)
 */
fastify.post('/presence', async (request, reply) => {
  const { jid, status, pushName, timestamp } = request.body;
  
  // Log opcional (pode gerar muito output)
  // fastify.log.debug({ msg: 'Presença', jid, status });

  // Aqui podemos processar presença ou notificar Python
  // Por ora, apenas confirmamos (o Python processa via handlers)
  
  return { success: true, jid, status };
});

// ================================
// Inicialização
// ================================
const start = async () => {
  try {
    const port = process.env.PORT || 5000;
    await fastify.listen({ port, host: '0.0.0.0' });
    
    console.log('\n');
    console.log('╔═══════════════════════════════════════════╗');
    console.log('║         🤖 JARVIS API - Online            ║');
    console.log('╠═══════════════════════════════════════════╣');
    console.log(`║  🌐 Porta: ${port}                            ║`);
    console.log('║  📡 Endpoints:                            ║');
    console.log('║     GET  /health   - Health check         ║');
    console.log('║     GET  /stats    - Estatísticas         ║');
    console.log('║     POST /webhook  - Receber mensagens    ║');
    if (API_QUEUE_ENABLED) {
      console.log('║     POST /queue    - Enfileirar (ACK)     ║');
    }
    console.log('║     POST /process  - Processar IA         ║');
    console.log('║     POST /send     - Enviar via WhatsApp  ║');
    console.log('║     POST /media    - Notificar mídia      ║');
    console.log('║     POST /presence - Notificar presença   ║');
    console.log('╚═══════════════════════════════════════════╝');
    console.log('\n');
    
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
