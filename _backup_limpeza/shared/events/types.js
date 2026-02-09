/**
 * JARVIS - Definição de Eventos
 * Contratos compartilhados entre services
 */

// Tipos de eventos
export const EventTypes = {
  // Mensagens
  MESSAGE_RECEIVED: 'message.received',
  MESSAGE_SENT: 'message.sent',
  MESSAGE_FAILED: 'message.failed',
  
  // Mídia
  MEDIA_RECEIVED: 'media.received',
  MEDIA_DOWNLOADED: 'media.downloaded',
  
  // Presença
  PRESENCE_UPDATE: 'presence.update',
  CONTACT_ONLINE: 'contact.online',
  CONTACT_OFFLINE: 'contact.offline',
  
  // Monitors
  KEYWORD_MATCH: 'monitor.keyword',
  VIP_MESSAGE: 'monitor.vip',
  SPAM_DETECTED: 'monitor.spam',
  
  // Scheduler
  SCHEDULE_CREATED: 'schedule.created',
  SCHEDULE_EXECUTED: 'schedule.executed',
  REMINDER_SENT: 'reminder.sent',
  
  // Sistema
  SERVICE_UP: 'system.service.up',
  SERVICE_DOWN: 'system.service.down',
  ERROR: 'system.error'
};

// Schema de eventos (para validação futura)
export const EventSchemas = {
  [EventTypes.MESSAGE_RECEIVED]: {
    sender: 'string',      // JID
    message: 'string',
    pushName: 'string',
    timestamp: 'number',
    isGroup: 'boolean',
    hasMedia: 'boolean',
    mediaType: 'string?'
  },
  
  [EventTypes.PRESENCE_UPDATE]: {
    jid: 'string',
    status: 'string',      // available | unavailable | composing | recording
    pushName: 'string?'
  },
  
  [EventTypes.KEYWORD_MATCH]: {
    keyword: 'string',
    sender: 'string',
    message: 'string',
    timestamp: 'number'
  }
};

export default EventTypes;
