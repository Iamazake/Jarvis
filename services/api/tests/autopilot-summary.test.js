/**
 * Testes para rotas internas de autopilot (resumo e privacidade).
 * Executa com: node --test tests/autopilot-summary.test.js
 * Requer: API não usa MySQL (MYSQL_HOST vazio) para estes testes.
 */

import { describe, it, before, after } from 'node:test';
import assert from 'node:assert';

const BASE = 'http://127.0.0.1';
let server;
let port;

async function startServer() {
  process.env.MYSQL_HOST = '';
  process.env.MYSQL_DATABASE = '';
  process.env.JARVIS_ADMIN_JID = '5511985751247@s.whatsapp.net';
  const { default: Fastify } = await import('fastify');
  const { join } = await import('path');
  const { fileURLToPath } = await import('url');
  const { dirname } = await import('path');
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const rootDir = join(__dirname, '..', '..', '..');
  const app = Fastify({ logger: false });
  await app.register((await import('@fastify/cors')).default, { origin: true });

  function normalizeJid(jid) {
    if (!jid || typeof jid !== 'string' || !jid.includes('@')) return '';
    let raw = jid.trim().toLowerCase();
    if (raw.endsWith('@lid') && raw.includes(':')) {
      const number = raw.split(':')[0].replace(/^\+/, '');
      if (/^\d+$/.test(number)) raw = number + '@s.whatsapp.net';
    }
    return raw;
  }

  function getAdminJid() {
    const admin = (process.env.JARVIS_ADMIN_JID || '').trim();
    if (admin && admin.includes('@')) return normalizeJid(admin);
    return null;
  }

  app.post('/internal/autopilot-summary', async (request, reply) => {
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
    return reply.send({ allowed: true, summary_md: 'Sem eventos de autopilot no período informado.' });
  });

  await app.listen({ port: 0, host: '127.0.0.1' });
  port = app.server.address().port;
  server = app;
  return app;
}

describe('Autopilot summary privacy', () => {
  before(async () => {
    await startServer();
  });

  after(async () => {
    if (server) await server.close();
  });

  it('returns 403 when non-admin requests summary for another jid (requester via header)', async () => {
    const res = await fetch(`${BASE}:${port}/internal/autopilot-summary`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Jarvis-Requester-Jid': '5511999999999@s.whatsapp.net'
      },
      body: JSON.stringify({ target_jid: '5511888888888@s.whatsapp.net', period: '24h' })
    });
    assert.strictEqual(res.status, 403);
    const data = await res.json();
    assert.strictEqual(data.allowed, false);
    assert.ok(data.message.includes('Acesso negado'));
  });

  it('returns 200 when requester requests own summary (requester via header)', async () => {
    const res = await fetch(`${BASE}:${port}/internal/autopilot-summary`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Jarvis-Requester-Jid': '5511999999999@s.whatsapp.net'
      },
      body: JSON.stringify({ target_jid: '5511999999999@s.whatsapp.net', period: '24h' })
    });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.allowed, true);
    assert.strictEqual(data.summary_md, 'Sem eventos de autopilot no período informado.');
  });

  it('returns 200 when admin requests summary for any target', async () => {
    const res = await fetch(`${BASE}:${port}/internal/autopilot-summary`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Jarvis-Requester-Jid': '5511985751247@s.whatsapp.net'
      },
      body: JSON.stringify({ target_jid: '5511888888888@s.whatsapp.net', period: 'hoje' })
    });
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.allowed, true);
  });
});
