/**
 * JARVIS - Configuração de Portas e URLs
 * Importado por todos os services
 */

export const SERVICES = {
  whatsapp: {
    port: process.env.PORT_WHATSAPP || 3001,
    url: `http://localhost:${process.env.PORT_WHATSAPP || 3001}`
  },
  api: {
    port: process.env.PORT_API || 5000,
    url: `http://localhost:${process.env.PORT_API || 5000}`
  },
  scheduler: {
    port: process.env.PORT_SCHEDULER || 5002,
    url: `http://localhost:${process.env.PORT_SCHEDULER || 5002}`
  },
  monitors: {
    port: process.env.PORT_MONITORS || 5003,
    url: `http://localhost:${process.env.PORT_MONITORS || 5003}`
  }
};

export const OWNER_NUMBER = process.env.OWNER_NUMBER || '';

export default SERVICES;
