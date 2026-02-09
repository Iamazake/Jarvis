/**
 * JARVIS WhatsApp Service - Baileys v6.5
 * Conexão estável sem Chrome/Selenium
 * MODO AUTÔNOMO - Responde automaticamente
 */

import pkg from '@whiskeysockets/baileys';
const { 
  default: makeWASocket,
  DisconnectReason, 
  useMultiFileAuthState,
  makeCacheableSignalKeyStore
} = pkg;
import qrcode from 'qrcode-terminal';
import pino from 'pino';
import { existsSync, mkdirSync, rmSync, writeFileSync, readFileSync } from 'fs';
import Fastify from 'fastify';

// ========================================
// Configurações
// ========================================
const CONFIG = {
  authDir: './auth_info',
  apiPort: 3001,
  // URLs dos outros serviços
  services: {
    api: 'http://localhost:5000',
    scheduler: 'http://localhost:5002',
    monitors: 'http://localhost:5003'
  },
  contactsFile: './contacts_cache.json',
  autoReply: true,  // MODO AUTÔNOMO ATIVADO
  ownerNumber: '5511988669454'  // Seu número (não responde a si mesmo)
};

// Logger silencioso (erros de init queries são esperados)
const logger = pino({ 
  level: 'silent'
});

// Estado global
let sock = null;
let isConnected = false;
let startTime = Date.now();
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

// Cache de contatos do WhatsApp
let contactsCache = {};

// ========================================
// Gerenciamento de Contatos
// ========================================
function loadContactsCache() {
  try {
    if (existsSync(CONFIG.contactsFile)) {
      contactsCache = JSON.parse(readFileSync(CONFIG.contactsFile, 'utf8'));
      console.log(`📒 ${Object.keys(contactsCache).length} contatos carregados do cache`);
    }
  } catch (e) {
    contactsCache = {};
  }
}

function saveContactsCache() {
  try {
    writeFileSync(CONFIG.contactsFile, JSON.stringify(contactsCache, null, 2));
  } catch (e) {
    console.error('Erro ao salvar cache de contatos:', e.message);
  }
}

function updateContact(jid, name, pushName) {
  const number = jid.replace('@s.whatsapp.net', '').replace('@g.us', '');
  if (!contactsCache[number]) {
    contactsCache[number] = {};
  }
  if (name) contactsCache[number].name = name;
  if (pushName) contactsCache[number].pushName = pushName;
  contactsCache[number].jid = jid;
  contactsCache[number].lastSeen = Date.now();
}

function findContactByName(query) {
  query = query.toLowerCase().trim();
  let bestMatch = null;
  let bestScore = 0;
  
  for (const [number, info] of Object.entries(contactsCache)) {
    const name = (info.name || info.pushName || '').toLowerCase();
    
    // Match exato
    if (name === query) {
      return { number, ...info, score: 1.0 };
    }
    
    // Contém o nome
    if (name.includes(query) || query.includes(name)) {
      const score = 0.8;
      if (score > bestScore) {
        bestScore = score;
        bestMatch = { number, ...info, score };
      }
      continue;
    }
    
    // Similaridade por partes
    const nameParts = name.split(' ');
    for (const part of nameParts) {
      if (part.includes(query) || query.includes(part)) {
        const score = 0.6;
        if (score > bestScore) {
          bestScore = score;
          bestMatch = { number, ...info, score };
        }
      }
    }
  }
  
  return bestMatch;
}

// ========================================
// Conexão WhatsApp
// ========================================
async function connectWhatsApp() {
  // Limpar auth antigo se muitas falhas
  if (reconnectAttempts > MAX_RECONNECT_ATTEMPTS) {
    console.log('🗑️ Limpando sessão antiga...');
    if (existsSync(CONFIG.authDir)) {
      rmSync(CONFIG.authDir, { recursive: true, force: true });
    }
    reconnectAttempts = 0;
  }

  // Criar diretório de auth se não existir
  if (!existsSync(CONFIG.authDir)) {
    mkdirSync(CONFIG.authDir, { recursive: true });
  }

  try {
    const { state, saveCreds } = await useMultiFileAuthState(CONFIG.authDir);
    
    console.log('🚀 Iniciando JARVIS WhatsApp (Baileys)...');
    console.log(`📦 Tentativa: ${reconnectAttempts + 1}`);

    sock = makeWASocket({
      auth: {
        creds: state.creds,
        keys: makeCacheableSignalKeyStore(state.keys, logger)
      },
      printQRInTerminal: true,
      logger,
      browser: ['JARVIS', 'Chrome', '120.0.0'],
      connectTimeoutMs: 120000,
      qrTimeout: 40000,
      retryRequestDelayMs: 2000,
      keepAliveIntervalMs: 30000,
      markOnlineOnConnect: false,
      syncFullHistory: false
    });

    // Salvar credenciais
    sock.ev.on('creds.update', saveCreds);

    // Eventos de conexão
    sock.ev.on('connection.update', (update) => {
      const { connection, lastDisconnect, qr } = update;
      
      console.log('📡 Connection update:', connection || 'waiting...');

      if (qr) {
        console.log('\n📱 Escaneie o QR Code com seu WhatsApp:');
        console.log('   WhatsApp > Menu > Dispositivos conectados > Conectar dispositivo\n');
      }

      if (connection === 'close') {
        isConnected = false;
        reconnectAttempts++;
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        const reason = DisconnectReason[statusCode] || statusCode;
        
        console.log(`⚠️ Desconectado: ${reason} (tentativa ${reconnectAttempts})`);
        
        // Reconectar se não foi logout
        if (statusCode !== DisconnectReason.loggedOut) {
          const delay = Math.min(5000 * reconnectAttempts, 30000);
          console.log(`🔄 Reconectando em ${delay/1000}s...`);
          setTimeout(connectWhatsApp, delay);
        } else {
          console.log('❌ Sessão encerrada. Execute novamente para novo QR.');
          // Limpar auth para forçar novo QR
          if (existsSync(CONFIG.authDir)) {
            rmSync(CONFIG.authDir, { recursive: true, force: true });
          }
          setTimeout(connectWhatsApp, 3000);
        }
      }

      if (connection === 'open') {
        isConnected = true;
        reconnectAttempts = 0;
        console.log('\n✅ WhatsApp conectado com sucesso!');
        console.log(`🤖 Modo Autônomo: ${CONFIG.autoReply ? 'ATIVADO' : 'desativado'}`);
        console.log('👂 Aguardando mensagens...\n');
        
        // Sincronizar contatos
        syncContacts();
      }
    });

    // Atualização de contatos do WhatsApp
    sock.ev.on('contacts.update', (updates) => {
      for (const contact of updates) {
        if (contact.id && contact.notify) {
          updateContact(contact.id, contact.notify, contact.notify);
        }
      }
      saveContactsCache();
    });

    // Receber mensagens
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
      if (type !== 'notify') return;
      
      for (const msg of messages) {
        // Ignorar mensagens próprias
        if (msg.key.fromMe) continue;
        
        const sender = msg.key.remoteJid;
        const pushName = msg.pushName || 'Usuário';
        const isGroup = sender.endsWith('@g.us');
        
        // Atualizar cache de contatos
        updateContact(sender, null, pushName);
        
        // Detectar tipo de mídia
        const mediaType = detectMediaType(msg);
        const hasMedia = mediaType !== null;
        
        // Extrair texto
        const text = msg.message?.conversation || 
                     msg.message?.extendedTextMessage?.text ||
                     msg.message?.imageMessage?.caption ||
                     msg.message?.videoMessage?.caption ||
                     '';
        
        // Log da mensagem
        if (text) {
          console.log(`📩 ${pushName}: ${text.substring(0, 50)}...`);
        } else if (hasMedia) {
          console.log(`📎 ${pushName}: [${mediaType}]`);
        }
        
        // Preparar payload
        const payload = {
          sender,
          message: text,
          pushName,
          timestamp: Date.now(),
          isGroup,
          hasMedia,
          mediaType,
          mimetype: getMessageMimetype(msg),
          caption: msg.message?.imageMessage?.caption || 
                   msg.message?.videoMessage?.caption || ''
        };
        
        // ========================================
        // Notificar serviços
        // ========================================
        
        // 1. Notificar Monitors Service (alertas, keywords, VIP)
        notifyService('monitors', '/webhook/message', payload);
        
        // 2. Se for mídia, notificar também o endpoint de mídia
        if (hasMedia) {
          notifyService('monitors', '/webhook/media', payload);
          notifyService('api', '/media', payload);
        }
        
        // 3. Só responder via IA se tiver texto
        if (!text) continue;
        
        // Processar via API Service (gera resposta com IA)
        try {
          const response = await fetch(`${CONFIG.services.api}/webhook`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          
          const result = await response.json();
          
          if (result.success && result.response) {
            await sendMessage(sender, result.response);
            console.log(`📤 Respondido: ${result.response.substring(0, 50)}...`);
          }
        } catch (error) {
          console.error('❌ Erro ao processar:', error.message);
        }
      }
    });

    // Monitorar presença (online/offline)
    sock.ev.on('presence.update', async (presence) => {
      const jid = presence.id;
      const presences = presence.presences || {};
      
      for (const [participantJid, status] of Object.entries(presences)) {
        const presenceStatus = status.lastKnownPresence || 'unknown';
        
        if (['available', 'unavailable', 'composing', 'recording'].includes(presenceStatus)) {
          // Notificar Monitors Service
          notifyService('monitors', '/webhook/presence', {
            jid: participantJid,
            status: presenceStatus,
            timestamp: Date.now()
          });
        }
      }
    });

  } catch (error) {
    console.error('❌ Erro ao conectar:', error.message);
    console.log('🔄 Tentando novamente em 10 segundos...');
    setTimeout(connectWhatsApp, 10000);
  }
}

// ========================================
// Sincronização de Contatos
// ========================================
async function syncContacts() {
  console.log('📒 Sincronizando contatos...');
  loadContactsCache();
  
  try {
    // No Baileys, contatos são aprendidos conforme mensagens chegam
    // A cache é persistida e cresce com o uso
    console.log(`📒 ${Object.keys(contactsCache).length} contatos no cache`);
    
    // Se cache vazio, mostrar dica
    if (Object.keys(contactsCache).length === 0) {
      console.log('💡 Dica: Contatos são aprendidos quando você recebe/envia mensagens');
      console.log('   Use "importar contatos" para importar da sua agenda');
    }
  } catch (e) {
    console.log('⚠️ Erro ao carregar contatos:', e.message);
  }
}

// Buscar todos os contatos do WhatsApp usando o onWhatsApp
async function fetchWhatsAppContacts(numbers) {
  try {
    if (!sock || !isConnected) return [];
    
    // Verificar quais números estão no WhatsApp
    const results = await sock.onWhatsApp(...numbers.map(n => n + '@s.whatsapp.net'));
    return results.map(r => ({
      number: r.jid.replace('@s.whatsapp.net', ''),
      jid: r.jid,
      exists: r.exists
    }));
  } catch (e) {
    console.error('Erro ao buscar contatos:', e.message);
    return [];
  }
}

// Adicionar contato manualmente ao cache
function addContactToCache(number, name) {
  const cleanNumber = number.replace(/\D/g, '');
  contactsCache[cleanNumber] = {
    name: name,
    pushName: name,
    jid: cleanNumber + '@s.whatsapp.net',
    lastSeen: Date.now(),
    manual: true
  };
  saveContactsCache();
  return contactsCache[cleanNumber];
}

// ========================================
// Funções Utilitárias
// ========================================

// Notificar outro serviço (fire and forget)
async function notifyService(serviceName, endpoint, payload) {
  const url = CONFIG.services[serviceName];
  if (!url) return;
  
  try {
    fetch(`${url}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).catch(() => {}); // Fire and forget
  } catch (err) {
    // Silencioso - não bloqueia o fluxo principal
  }
}

// Detectar tipo de mídia na mensagem
function detectMediaType(msg) {
  if (msg.message?.imageMessage) return 'image';
  if (msg.message?.videoMessage) return 'video';
  if (msg.message?.audioMessage) return 'audio';
  if (msg.message?.documentMessage) return 'document';
  if (msg.message?.stickerMessage) return 'sticker';
  if (msg.message?.contactMessage) return 'contact';
  if (msg.message?.locationMessage) return 'location';
  return null;
}

// Obter mimetype da mídia
function getMessageMimetype(msg) {
  return msg.message?.imageMessage?.mimetype ||
         msg.message?.videoMessage?.mimetype ||
         msg.message?.audioMessage?.mimetype ||
         msg.message?.documentMessage?.mimetype ||
         msg.message?.stickerMessage?.mimetype ||
         '';
}

// Notificar Python sobre mídia recebida (legado - manter compatibilidade)
async function notifyPythonMedia(payload) {
  notifyService('api', '/media', payload);
}

// Notificar Python sobre presença
async function notifyPythonPresence(jid, status, pushName) {
  notifyService('monitors', '/webhook/presence', {
    jid,
    status,
    pushName,
    timestamp: Date.now()
  });
}

async function sendMessage(to, text) {
  if (!sock || !isConnected) {
    throw new Error('WhatsApp não conectado');
  }
  
  await sock.sendMessage(to, { text });
}

function formatUptime() {
  const seconds = Math.floor((Date.now() - startTime) / 1000);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

// ========================================
// API HTTP
// ========================================
const fastify = Fastify({ logger: false });

// Status
fastify.get('/status', async () => ({
  connected: isConnected,
  uptime: formatUptime(),
  autoReply: CONFIG.autoReply,
  contactsCount: Object.keys(contactsCache).length,
  timestamp: Date.now()
}));

// Listar contatos
fastify.get('/contacts', async () => {
  return {
    success: true,
    count: Object.keys(contactsCache).length,
    contacts: contactsCache
  };
});

// Buscar contato por nome
fastify.get('/contacts/search', async (request, reply) => {
  const { q } = request.query || {};
  
  if (!q) {
    return reply.status(400).send({ error: 'Parâmetro q (query) é obrigatório' });
  }
  
  const match = findContactByName(q);
  
  if (match) {
    return { success: true, contact: match };
  } else {
    return { success: false, message: 'Contato não encontrado' };
  }
});

// Enviar mensagem por nome
fastify.post('/send-by-name', async (request, reply) => {
  const { name, message } = request.body || {};
  
  if (!name || !message) {
    return reply.status(400).send({ error: 'name e message são obrigatórios' });
  }
  
  if (!isConnected) {
    return reply.status(503).send({ error: 'WhatsApp não conectado' });
  }
  
  // Buscar contato pelo nome
  const contact = findContactByName(name);
  
  if (!contact) {
    return reply.status(404).send({ 
      success: false, 
      error: `Contato "${name}" não encontrado`,
      hint: 'Use /contacts para ver contatos disponíveis'
    });
  }
  
  try {
    const jid = contact.jid || `${contact.number}@s.whatsapp.net`;
    await sendMessage(jid, message);
    
    return { 
      success: true, 
      sentTo: contact.name || contact.pushName || contact.number,
      number: contact.number
    };
  } catch (error) {
    return reply.status(500).send({ error: error.message });
  }
});

// Ativar/desativar modo autônomo
fastify.post('/auto-reply', async (request, reply) => {
  const { enabled } = request.body || {};
  
  if (typeof enabled === 'boolean') {
    CONFIG.autoReply = enabled;
    console.log(`🤖 Modo Autônomo: ${enabled ? 'ATIVADO' : 'desativado'}`);
    return { success: true, autoReply: CONFIG.autoReply };
  }
  
  return { autoReply: CONFIG.autoReply };
});

// Adicionar contato manualmente
fastify.post('/contacts/add', async (request, reply) => {
  const { number, name } = request.body || {};
  
  if (!number || !name) {
    return reply.status(400).send({ error: 'number e name são obrigatórios' });
  }
  
  const contact = addContactToCache(number, name);
  
  return { 
    success: true, 
    message: `Contato "${name}" adicionado`,
    contact 
  };
});

// Importar vários contatos de uma vez
fastify.post('/contacts/import', async (request, reply) => {
  const { contacts } = request.body || {};
  
  if (!contacts || !Array.isArray(contacts)) {
    return reply.status(400).send({ 
      error: 'contacts deve ser um array', 
      example: [{ number: '5511999999999', name: 'João' }] 
    });
  }
  
  let imported = 0;
  for (const c of contacts) {
    if (c.number && c.name) {
      addContactToCache(c.number, c.name);
      imported++;
    }
  }
  
  return { 
    success: true, 
    imported,
    total: Object.keys(contactsCache).length 
  };
});

// Enviar mensagem (por número)
fastify.post('/send', async (request, reply) => {
  const { to, message } = request.body || {};
  
  if (!to || !message) {
    return reply.status(400).send({ error: 'to e message são obrigatórios' });
  }
  
  if (!isConnected) {
    return reply.status(503).send({ error: 'WhatsApp não conectado' });
  }
  
  try {
    // Formatar número se necessário
    let jid = to;
    if (!jid.includes('@')) {
      jid = jid.replace(/\D/g, '') + '@s.whatsapp.net';
    }
    
    await sendMessage(jid, message);
    return { success: true, to: jid };
  } catch (error) {
    return reply.status(500).send({ error: error.message });
  }
});

// Health check
fastify.get('/health', async () => ({
  status: 'ok',
  connected: isConnected
}));

// ========================================
// Inicialização
// ========================================
async function main() {
  console.log('══════════════════════════════════════════════════');
  console.log('  🤖 JARVIS WhatsApp Service');
  console.log('  Powered by Baileys (sem Chrome!)');
  console.log('══════════════════════════════════════════════════');
  
  // Iniciar API
  try {
    await fastify.listen({ port: CONFIG.apiPort, host: '0.0.0.0' });
    console.log(`📡 API rodando em http://localhost:${CONFIG.apiPort}`);
    console.log('   POST /send { to, message }');
    console.log('   GET  /status');
  } catch (err) {
    console.error('❌ Erro ao iniciar API:', err.message);
    process.exit(1);
  }
  
  // Conectar WhatsApp
  await connectWhatsApp();
}

// Tratamento de erros
process.on('uncaughtException', (err) => {
  console.error('❌ Erro não tratado:', err.message);
});

process.on('unhandledRejection', (err) => {
  console.error('❌ Promise rejeitada:', err.message);
});

process.on('SIGINT', () => {
  console.log('\n👋 Encerrando...');
  process.exit(0);
});

// Executar
main();
