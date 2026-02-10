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
import { readFileSync } from 'fs';

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

// ================================
// Funções Utilitárias
// ================================

/**
 * Executa comando Python para processar mensagem via JARVIS (run_jarvis_message.py).
 * Usa JID (from_jid) para decisão de autopilot; display_name só para exibição.
 */
async function processPythonAI(message, jid, displayName) {
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
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    });

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(stdout.trim());
          resolve(result);
        } catch (e) {
          // Se não for JSON, retorna como texto
          resolve({ response: stdout.trim(), cached: false });
        }
      } else {
        reject(new Error(stderr || `Python exited with code ${code}`));
      }
    });

    python.on('error', (err) => {
      reject(err);
    });
  });
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
    processing: state.processing
  };
});

/**
 * Webhook - Recebe mensagens do WhatsApp (Baileys)
 */
fastify.post('/webhook', async (request, reply) => {
  const { sender, message, timestamp, pushName, from_jid, display_name } = request.body;
  const jid = from_jid || sender;
  const displayName = display_name || pushName || '';

  if (!message || !jid) {
    return reply.status(400).send({ error: 'sender/from_jid e message são obrigatórios' });
  }

  state.stats.received++;
  
  fastify.log.info({
    msg: 'Mensagem recebida',
    jid,
    displayName: displayName || '(sem nome)',
    message: message.substring(0, 100)
  });

  try {
    // Decisão reply/ignore só via Python (autopilot). Nunca usar quickResponse aqui:
    // senão responderíamos "Olá!" mesmo com autopilot desativado.
    const result = await processPythonAI(message, jid, displayName);

    state.stats.processed++;

    return {
      success: true,
      action: result.action || 'reply',
      response: result.response ?? '',
      cached: result.cached || false,
      sender,
      reason: result.reason
    };

  } catch (error) {
    state.stats.errors++;
    fastify.log.error({ msg: 'Erro ao processar', error: error.message });

    // Não enviar mensagem genérica (evita "Olá" ou greeting em caso de fetch/erro)
    return {
      success: false,
      action: 'ignore',
      response: '',
      reason: 'error',
      error: error.message
    };
  }
});

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
