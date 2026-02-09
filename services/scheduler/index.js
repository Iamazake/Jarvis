/**
 * JARVIS Scheduler Service
 * 
 * Responsabilidade única: Agendar mensagens e lembretes
 * Porta: 5002
 * 
 * Comunica via:
 * - POST localhost:3001/send (enviar mensagem)
 * - POST localhost:5000/generate (gerar texto com IA)
 */

import Fastify from 'fastify';
import cron from 'node-cron';
import { readFileSync, writeFileSync, existsSync } from 'fs';

const fastify = Fastify({ logger: false });
const PORT = 5002;
const SCHEDULES_FILE = './schedules.json';

// ========================================
// Estado
// ========================================
let schedules = [];
let activeCrons = new Map();

// ========================================
// Persistência
// ========================================
function loadSchedules() {
  try {
    if (existsSync(SCHEDULES_FILE)) {
      schedules = JSON.parse(readFileSync(SCHEDULES_FILE, 'utf8'));
      console.log(`📅 ${schedules.length} agendamentos carregados`);
    }
  } catch (e) {
    schedules = [];
  }
}

function saveSchedules() {
  writeFileSync(SCHEDULES_FILE, JSON.stringify(schedules, null, 2));
}

// ========================================
// Funções de Agendamento
// ========================================
function scheduleJob(schedule) {
  const { id, cronExpression, contactNumber, message, enabled } = schedule;
  
  if (!enabled) return;
  
  // Cancelar job anterior se existir
  if (activeCrons.has(id)) {
    activeCrons.get(id).stop();
  }
  
  const job = cron.schedule(cronExpression, async () => {
    console.log(`⏰ Executando agendamento: ${id}`);
    
    try {
      // Enviar via WhatsApp service
      const response = await fetch('http://localhost:3001/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to: contactNumber,
          message: message
        })
      });
      
      if (response.ok) {
        console.log(`✅ Mensagem agendada enviada para ${contactNumber}`);
        
        // Atualizar lastRun
        const idx = schedules.findIndex(s => s.id === id);
        if (idx >= 0) {
          schedules[idx].lastRun = new Date().toISOString();
          schedules[idx].runCount = (schedules[idx].runCount || 0) + 1;
          saveSchedules();
        }
      }
    } catch (error) {
      console.error(`❌ Erro ao enviar agendamento ${id}:`, error.message);
    }
  });
  
  activeCrons.set(id, job);
  console.log(`📅 Job ${id} agendado: ${cronExpression}`);
}

function initializeAllJobs() {
  schedules.forEach(schedule => {
    if (schedule.enabled) {
      scheduleJob(schedule);
    }
  });
}

// ========================================
// API Endpoints
// ========================================

// Health check
fastify.get('/health', async () => ({
  status: 'ok',
  service: 'scheduler',
  activeJobs: activeCrons.size,
  totalSchedules: schedules.length
}));

// Listar agendamentos
fastify.get('/schedules', async () => ({
  success: true,
  schedules
}));

// Criar agendamento
fastify.post('/schedules', async (request, reply) => {
  const { 
    contactNumber, 
    contactName,
    message, 
    cronExpression,
    description 
  } = request.body;
  
  if (!contactNumber || !message || !cronExpression) {
    return reply.status(400).send({ 
      error: 'contactNumber, message e cronExpression são obrigatórios' 
    });
  }
  
  // Validar cron
  if (!cron.validate(cronExpression)) {
    return reply.status(400).send({ error: 'cronExpression inválida' });
  }
  
  const schedule = {
    id: `sched_${Date.now()}`,
    contactNumber,
    contactName: contactName || contactNumber,
    message,
    cronExpression,
    description: description || '',
    enabled: true,
    createdAt: new Date().toISOString(),
    lastRun: null,
    runCount: 0
  };
  
  schedules.push(schedule);
  saveSchedules();
  scheduleJob(schedule);
  
  return { success: true, schedule };
});

// Criar lembrete único (one-time)
fastify.post('/reminders', async (request, reply) => {
  const { 
    contactNumber, 
    contactName,
    message, 
    datetime,
    generateWithAI,
    aiPrompt
  } = request.body;
  
  if (!contactNumber || !datetime) {
    return reply.status(400).send({ 
      error: 'contactNumber e datetime são obrigatórios' 
    });
  }
  
  const targetDate = new Date(datetime);
  const now = new Date();
  
  if (targetDate <= now) {
    return reply.status(400).send({ error: 'datetime deve ser no futuro' });
  }
  
  // Calcular delay em ms
  const delay = targetDate.getTime() - now.getTime();
  
  let finalMessage = message;
  
  // Se pediu para gerar com IA
  if (generateWithAI && aiPrompt) {
    try {
      const aiResponse = await fetch('http://localhost:5000/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: aiPrompt })
      });
      const aiData = await aiResponse.json();
      if (aiData.success) {
        finalMessage = aiData.response;
      }
    } catch (e) {
      console.error('Erro ao gerar com IA:', e.message);
    }
  }
  
  if (!finalMessage) {
    return reply.status(400).send({ error: 'message é obrigatória (ou generateWithAI + aiPrompt)' });
  }
  
  const reminder = {
    id: `rem_${Date.now()}`,
    contactNumber,
    contactName: contactName || contactNumber,
    message: finalMessage,
    scheduledFor: datetime,
    createdAt: new Date().toISOString(),
    status: 'pending'
  };
  
  // Agendar execução
  setTimeout(async () => {
    try {
      const response = await fetch('http://localhost:3001/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to: contactNumber,
          message: finalMessage
        })
      });
      
      if (response.ok) {
        console.log(`✅ Lembrete ${reminder.id} enviado`);
        reminder.status = 'sent';
      } else {
        reminder.status = 'failed';
      }
    } catch (error) {
      console.error(`❌ Erro no lembrete ${reminder.id}:`, error.message);
      reminder.status = 'failed';
    }
  }, delay);
  
  console.log(`⏰ Lembrete agendado para ${datetime} (em ${Math.round(delay/60000)} minutos)`);
  
  return { 
    success: true, 
    reminder,
    willRunIn: `${Math.round(delay/60000)} minutos`
  };
});

// Ativar/desativar agendamento
fastify.patch('/schedules/:id', async (request, reply) => {
  const { id } = request.params;
  const { enabled } = request.body;
  
  const idx = schedules.findIndex(s => s.id === id);
  if (idx < 0) {
    return reply.status(404).send({ error: 'Agendamento não encontrado' });
  }
  
  schedules[idx].enabled = enabled;
  saveSchedules();
  
  if (enabled) {
    scheduleJob(schedules[idx]);
  } else if (activeCrons.has(id)) {
    activeCrons.get(id).stop();
    activeCrons.delete(id);
  }
  
  return { success: true, schedule: schedules[idx] };
});

// Deletar agendamento
fastify.delete('/schedules/:id', async (request, reply) => {
  const { id } = request.params;
  
  const idx = schedules.findIndex(s => s.id === id);
  if (idx < 0) {
    return reply.status(404).send({ error: 'Agendamento não encontrado' });
  }
  
  // Parar job se existir
  if (activeCrons.has(id)) {
    activeCrons.get(id).stop();
    activeCrons.delete(id);
  }
  
  schedules.splice(idx, 1);
  saveSchedules();
  
  return { success: true, message: 'Agendamento removido' };
});

// ========================================
// Inicialização
// ========================================
async function start() {
  loadSchedules();
  initializeAllJobs();
  
  await fastify.listen({ port: PORT, host: '0.0.0.0' });
  
  console.log('');
  console.log('╔═══════════════════════════════════════════╗');
  console.log('║      ⏰ JARVIS Scheduler - Online         ║');
  console.log('╠═══════════════════════════════════════════╣');
  console.log(`║  🌐 Porta: ${PORT}                            ║`);
  console.log('║  📡 Endpoints:                            ║');
  console.log('║     GET  /health     - Status             ║');
  console.log('║     GET  /schedules  - Listar             ║');
  console.log('║     POST /schedules  - Criar recorrente   ║');
  console.log('║     POST /reminders  - Criar único        ║');
  console.log('╚═══════════════════════════════════════════╝');
  console.log('');
}

start();
