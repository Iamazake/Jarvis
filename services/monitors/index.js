/**
 * JARVIS Monitors Service
 * 
 * Responsabilidade única: Escutar eventos e disparar alertas
 * Porta: 5003
 * 
 * Recebe webhooks de:
 * - whatsapp (porta 3001) → mensagens, mídia, presença
 * 
 * Dispara alertas via:
 * - POST localhost:3001/send (notificar você)
 */

import Fastify from 'fastify';
import { readFileSync, writeFileSync, existsSync } from 'fs';

const fastify = Fastify({ logger: false });
const PORT = 5003;
const CONFIG_FILE = './monitors_config.json';

// ========================================
// Configuração
// ========================================
let config = {
  notifier: null, // Seu número para receber alertas
  
  keywords: {
    enabled: false,
    words: [],
    ignoreGroups: true
  },
  
  contacts: {
    enabled: false,
    vipContacts: [], // JIDs de contatos VIP
    notifyOnMessage: true,
    notifyOnOnline: false
  },
  
  media: {
    enabled: false,
    saveImages: true,
    saveVideos: false,
    saveAudios: false
  },
  
  presence: {
    enabled: false,
    trackContacts: [] // JIDs para monitorar presença
  },
  
  antiSpam: {
    enabled: false,
    maxMessagesPerMinute: 10,
    blockDuration: 60 // segundos
  }
};

// Estado
const stats = {
  messagesProcessed: 0,
  alertsSent: 0,
  keywordMatches: 0,
  vipMessages: 0,
  mediaReceived: 0
};

const messageCount = new Map(); // Para anti-spam
const blockedUsers = new Map();

// ========================================
// Persistência
// ========================================
function loadConfig() {
  try {
    if (existsSync(CONFIG_FILE)) {
      config = { ...config, ...JSON.parse(readFileSync(CONFIG_FILE, 'utf8')) };
      console.log('📋 Configuração carregada');
    }
  } catch (e) {
    console.warn('⚠️ Usando configuração padrão');
  }
}

function saveConfig() {
  writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
}

// ========================================
// Funções de Alerta
// ========================================
async function sendAlert(message) {
  if (!config.notifier) {
    console.warn('⚠️ Notifier não configurado');
    return false;
  }
  
  try {
    const response = await fetch('http://localhost:3001/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        to: config.notifier,
        message: `🚨 JARVIS Alert\n\n${message}`
      })
    });
    
    if (response.ok) {
      stats.alertsSent++;
      return true;
    }
  } catch (error) {
    console.error('❌ Erro ao enviar alerta:', error.message);
  }
  return false;
}

// ========================================
// Processadores de Eventos
// ========================================

// Processar mensagem
async function processMessage(data) {
  const { sender, message, pushName, isGroup, timestamp } = data;
  stats.messagesProcessed++;
  
  // Anti-spam check
  if (config.antiSpam.enabled) {
    const now = Date.now();
    const userKey = sender;
    
    // Verificar se está bloqueado
    if (blockedUsers.has(userKey)) {
      const blockUntil = blockedUsers.get(userKey);
      if (now < blockUntil) {
        console.log(`🚫 Mensagem de ${pushName} ignorada (bloqueado)`);
        return { blocked: true };
      } else {
        blockedUsers.delete(userKey);
      }
    }
    
    // Contar mensagens
    if (!messageCount.has(userKey)) {
      messageCount.set(userKey, []);
    }
    const times = messageCount.get(userKey);
    times.push(now);
    
    // Limpar mensagens antigas (> 1 minuto)
    const recentTimes = times.filter(t => now - t < 60000);
    messageCount.set(userKey, recentTimes);
    
    // Verificar limite
    if (recentTimes.length > config.antiSpam.maxMessagesPerMinute) {
      blockedUsers.set(userKey, now + (config.antiSpam.blockDuration * 1000));
      await sendAlert(`🚫 SPAM detectado!\n\nUsuário: ${pushName}\nMensagens: ${recentTimes.length}/min\nBloqueado por ${config.antiSpam.blockDuration}s`);
      return { blocked: true, reason: 'spam' };
    }
  }
  
  // Verificar keywords
  if (config.keywords.enabled && message) {
    if (config.keywords.ignoreGroups && isGroup) {
      // Ignorar grupos
    } else {
      const lowerMsg = message.toLowerCase();
      for (const keyword of config.keywords.words) {
        if (lowerMsg.includes(keyword.toLowerCase())) {
          stats.keywordMatches++;
          await sendAlert(`🔑 Keyword detectada: "${keyword}"\n\nDe: ${pushName}\nMsg: ${message.substring(0, 200)}`);
          break;
        }
      }
    }
  }
  
  // Verificar contato VIP
  if (config.contacts.enabled && config.contacts.notifyOnMessage) {
    if (config.contacts.vipContacts.includes(sender)) {
      stats.vipMessages++;
      await sendAlert(`⭐ Mensagem de VIP!\n\nDe: ${pushName}\nMsg: ${message?.substring(0, 200) || '[mídia]'}`);
    }
  }
  
  return { processed: true };
}

// Processar mídia
async function processMedia(data) {
  const { sender, pushName, mediaType, mimetype } = data;
  stats.mediaReceived++;
  
  if (!config.media.enabled) return { processed: false };
  
  // Verificar se deve notificar
  const shouldNotify = 
    (mediaType === 'image' && config.media.saveImages) ||
    (mediaType === 'video' && config.media.saveVideos) ||
    (mediaType === 'audio' && config.media.saveAudios);
  
  if (shouldNotify) {
    await sendAlert(`📎 Mídia recebida!\n\nDe: ${pushName}\nTipo: ${mediaType}\nFormato: ${mimetype}`);
  }
  
  return { processed: true };
}

// Processar presença (online/offline)
async function processPresence(data) {
  const { jid, status, pushName } = data;
  
  if (!config.presence.enabled) return { processed: false };
  
  if (config.presence.trackContacts.includes(jid)) {
    if (status === 'available') {
      await sendAlert(`🟢 ${pushName || jid} ficou ONLINE`);
    } else if (status === 'unavailable') {
      await sendAlert(`⚪ ${pushName || jid} ficou OFFLINE`);
    }
  }
  
  return { processed: true };
}

// ========================================
// API Endpoints
// ========================================

// Health
fastify.get('/health', async () => ({
  status: 'ok',
  service: 'monitors',
  stats,
  config: {
    notifier: config.notifier ? '✅ Configurado' : '❌ Não configurado',
    keywords: config.keywords.enabled ? `✅ ${config.keywords.words.length} palavras` : '❌',
    contacts: config.contacts.enabled ? `✅ ${config.contacts.vipContacts.length} VIPs` : '❌',
    media: config.media.enabled ? '✅' : '❌',
    presence: config.presence.enabled ? '✅' : '❌',
    antiSpam: config.antiSpam.enabled ? '✅' : '❌'
  }
}));

// Configuração
fastify.get('/config', async () => ({ success: true, config }));

fastify.put('/config', async (request, reply) => {
  const updates = request.body;
  config = { ...config, ...updates };
  saveConfig();
  return { success: true, config };
});

// Webhook de mensagem (chamado pelo whatsapp service)
fastify.post('/webhook/message', async (request, reply) => {
  return await processMessage(request.body);
});

// Webhook de mídia
fastify.post('/webhook/media', async (request, reply) => {
  return await processMedia(request.body);
});

// Webhook de presença
fastify.post('/webhook/presence', async (request, reply) => {
  return await processPresence(request.body);
});

// Adicionar keyword
fastify.post('/keywords', async (request, reply) => {
  const { word } = request.body;
  if (!word) return reply.status(400).send({ error: 'word é obrigatório' });
  
  if (!config.keywords.words.includes(word)) {
    config.keywords.words.push(word);
    saveConfig();
  }
  return { success: true, keywords: config.keywords.words };
});

// Remover keyword
fastify.delete('/keywords/:word', async (request, reply) => {
  const { word } = request.params;
  config.keywords.words = config.keywords.words.filter(w => w !== word);
  saveConfig();
  return { success: true, keywords: config.keywords.words };
});

// Adicionar contato VIP
fastify.post('/vip', async (request, reply) => {
  const { jid, number } = request.body;
  const contactJid = jid || `${number}@s.whatsapp.net`;
  
  if (!config.contacts.vipContacts.includes(contactJid)) {
    config.contacts.vipContacts.push(contactJid);
    saveConfig();
  }
  return { success: true, vipContacts: config.contacts.vipContacts };
});

// Remover contato VIP
fastify.delete('/vip/:jid', async (request, reply) => {
  const { jid } = request.params;
  config.contacts.vipContacts = config.contacts.vipContacts.filter(c => c !== jid);
  saveConfig();
  return { success: true, vipContacts: config.contacts.vipContacts };
});

// Configurar notifier (seu número)
fastify.post('/notifier', async (request, reply) => {
  const { number } = request.body;
  if (!number) return reply.status(400).send({ error: 'number é obrigatório' });
  
  config.notifier = `${number.replace(/\D/g, '')}@s.whatsapp.net`;
  saveConfig();
  return { success: true, notifier: config.notifier };
});

// Stats
fastify.get('/stats', async () => ({ success: true, stats }));

// ========================================
// Inicialização
// ========================================
async function start() {
  loadConfig();
  
  await fastify.listen({ port: PORT, host: '0.0.0.0' });
  
  console.log('');
  console.log('╔═══════════════════════════════════════════╗');
  console.log('║      👁️ JARVIS Monitors - Online          ║');
  console.log('╠═══════════════════════════════════════════╣');
  console.log(`║  🌐 Porta: ${PORT}                            ║`);
  console.log('║  📡 Webhooks:                             ║');
  console.log('║     POST /webhook/message  - Mensagens    ║');
  console.log('║     POST /webhook/media    - Mídia        ║');
  console.log('║     POST /webhook/presence - Presença     ║');
  console.log('╠═══════════════════════════════════════════╣');
  console.log('║  ⚙️  Endpoints:                            ║');
  console.log('║     GET/PUT /config - Configuração        ║');
  console.log('║     POST /keywords  - Add keyword         ║');
  console.log('║     POST /vip       - Add contato VIP     ║');
  console.log('║     POST /notifier  - Seu número          ║');
  console.log('╚═══════════════════════════════════════════╝');
  console.log('');
}

start();
