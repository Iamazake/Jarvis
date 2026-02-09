#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS WhatsApp - v4.0
Assistente Inteligente para WhatsApp

Chrome Anti-Detecção + Cache Semântico FAISS + IA Conversacional

Autor: JARVIS Team
Versão: 4.0.0
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

# Adicionar src ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Configurar logging
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"jarvis_{datetime.now():%Y%m%d}.log")
    ]
)
logger = logging.getLogger(__name__)

# Imports do JARVIS
from src.whatsapp import WhatsAppClient, MessageHandler, ContactProfile
from src.whatsapp.handlers import ContactType, DEFAULT_PROFILES
from src.ai import AIEngine
from src.database import Database

# Configurações
CONFIG_FILE = BASE_DIR / "config.json"
ENV_FILE = BASE_DIR / ".env"


def load_config() -> Dict:
    """Carrega configurações"""
    config = {
        "provider": "openai",
        "api_key": "",
        "model": "gpt-4o-mini",
        "use_cache": True,
    }
    
    # Carregar de arquivo
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                config.update(json.load(f))
        except:
            pass
    
    # Sobrescrever com variáveis de ambiente
    if os.getenv("OPENAI_API_KEY"):
        config["api_key"] = os.getenv("OPENAI_API_KEY")
        config["provider"] = "openai"
    elif os.getenv("ANTHROPIC_API_KEY"):
        config["api_key"] = os.getenv("ANTHROPIC_API_KEY")
        config["provider"] = "claude"
    
    # Carregar .env se existir
    if ENV_FILE.exists():
        try:
            with open(ENV_FILE) as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value.strip('"\'')
                        
                        if key == "OPENAI_API_KEY":
                            config["api_key"] = value.strip('"\'')
                            config["provider"] = "openai"
        except:
            pass
    
    return config


class JarvisWhatsApp:
    """
    Aplicação principal do JARVIS WhatsApp
    
    Facade Pattern: Interface unificada para todos os módulos
    """
    
    def __init__(self):
        self.config = load_config()
        self.whatsapp: Optional[WhatsAppClient] = None
        self.ai: Optional[AIEngine] = None
        self.db: Optional[Database] = None
        self.handler = MessageHandler()
        
        # Criar perfis padrão
        self.handler.create_default_profiles()
    
    def start(self) -> bool:
        """Inicializa todos os componentes"""
        print("\n" + "=" * 60)
        print("  🤖 JARVIS WhatsApp v4.0")
        print("  Chrome Anti-Detecção + Cache FAISS + IA")
        print("=" * 60)
        print(f"  📅 {datetime.now():%d/%m/%Y %H:%M}")
        print(f"  🧠 IA: {self.config.get('provider', 'N/A')}")
        print(f"  📦 Cache: {'Ativo' if self.config.get('use_cache') else 'Inativo'}")
        print("=" * 60 + "\n")
        
        # Inicializar banco de dados
        try:
            self.db = Database()
            logger.info("✅ Banco de dados conectado")
        except Exception as e:
            logger.warning(f"⚠️ Banco de dados: {e}")
        
        # Inicializar IA
        if self.config.get("api_key"):
            self.ai = AIEngine(self.config)
        else:
            logger.warning("⚠️ API Key não configurada - IA desativada")
        
        # Inicializar WhatsApp
        print("🚀 Iniciando WhatsApp...")
        self.whatsapp = WhatsAppClient()
        
        if not self.whatsapp.connect():
            logger.error("❌ Falha ao conectar WhatsApp")
            return False
        
        print("\n" + "=" * 60)
        print("  ✅ WhatsApp conectado!")
        print("=" * 60 + "\n")
        
        return True
    
    def run(self):
        """Loop principal"""
        if not self.start():
            return
        
        while True:
            try:
                self._show_menu()
                choice = input("\n👉 Escolha: ").strip()
                
                if choice == "0":
                    self._exit()
                    break
                elif choice == "1":
                    self._send_message()
                elif choice == "2":
                    self._read_messages()
                elif choice == "3":
                    self._monitor()
                elif choice == "4":
                    self._show_status()
                elif choice == "5":
                    self._add_monitored()
                elif choice == "6":
                    self._configure_profile()
                elif choice == "7":
                    self._reconnect()
                else:
                    print("❌ Opção inválida")
                    
            except KeyboardInterrupt:
                self._exit()
                break
            except Exception as e:
                logger.error(f"Erro: {e}")
    
    def _show_menu(self):
        """Exibe menu principal"""
        print("\n" + "=" * 60)
        print("  📱 MENU PRINCIPAL")
        print("=" * 60)
        print("  1. 📤 Enviar mensagem (com IA)")
        print("  2. 📥 Ler mensagens")
        print("  3. 👁️  Monitorar conversas")
        print("  4. 📊 Status do sistema")
        print("  5. ➕ Adicionar contato monitorado")
        print("  6. 👤 Configurar perfil de contato")
        print("  7. 🔄 Reconectar WhatsApp")
        print("  0. 🚪 Sair")
        print("=" * 60)
    
    def _send_message(self):
        """Envia mensagem com IA"""
        contact = input("📱 Contato: ").strip()
        if not contact:
            return
        
        # Obter ou criar perfil
        profile = self.handler.get_profile(contact)
        if not profile:
            print("\n📝 Perfil não encontrado. Usando padrão (amigo)")
            profile = DEFAULT_PROFILES["amigo"]
            profile.name = contact
        
        print(f"\n👤 Perfil: {profile.name} ({profile.contact_type.value})")
        
        # Abrir chat
        if not self.whatsapp.open_chat(contact):
            print("❌ Não foi possível abrir o chat")
            return
        
        # Obter contexto
        messages = self.whatsapp.get_last_messages(5)
        if messages:
            print("\n📜 Últimas mensagens:")
            for msg in messages[-3:]:
                sender = "👤" if msg.get("is_incoming") else "📤"
                print(f"  {sender} {msg.get('text', '')[:50]}")
        
        # Instrução
        print("\n💬 Como devo responder?")
        instruction = input("   (ou deixe vazio para resposta automática): ").strip()
        
        if not instruction:
            instruction = "Responda de forma natural e apropriada"
        
        # Gerar resposta
        if self.ai:
            print("\n🤖 Gerando resposta...")
            response, meta = self.ai.generate(
                profile=profile.to_dict(),
                message=messages[-1].get("text", "") if messages else "",
                instruction=instruction,
                history=profile.conversation_history
            )
            
            print(f"\n💬 Resposta gerada ({meta.get('source', 'unknown')}):")
            print(f"   {response}")
            
            # Confirmar
            confirm = input("\n✅ Enviar? (s/n/e para editar): ").strip().lower()
            
            if confirm == "e":
                response = input("📝 Nova mensagem: ").strip()
                confirm = "s"
            
            if confirm == "s" and response:
                if self.whatsapp.send_to_current_chat(response):
                    print("✅ Mensagem enviada!")
                    profile.add_message("assistant", response)
                else:
                    print("❌ Falha ao enviar")
            else:
                print("❌ Cancelado")
        else:
            # Sem IA - envio manual
            message = input("\n📝 Digite a mensagem: ").strip()
            if message:
                if self.whatsapp.send_to_current_chat(message):
                    print("✅ Enviada!")
                else:
                    print("❌ Falha")
    
    def _read_messages(self):
        """Lê mensagens de um contato"""
        contact = input("📱 Contato: ").strip()
        if not contact:
            return
        
        if self.whatsapp.open_chat(contact):
            messages = self.whatsapp.get_last_messages(10)
            
            print(f"\n📜 Mensagens de {contact}:")
            print("-" * 40)
            
            for msg in messages:
                sender = "👤" if msg.get("is_incoming") else "📤"
                text = msg.get("text", "")[:100]
                print(f"{sender} {text}")
            
            print("-" * 40)
        else:
            print("❌ Não foi possível abrir o chat")
    
    def _monitor(self):
        """Monitora mensagens em tempo real"""
        print("\n👁️ Contatos monitorados:")
        
        if not self.handler.monitored_contacts:
            print("   Nenhum contato configurado")
            print("   Use a opção 5 para adicionar")
            return
        
        for c in self.handler.monitored_contacts:
            print(f"   • {c}")
        
        print("\n🔄 Iniciando monitoramento... (Ctrl+C para parar)")
        
        def on_message(msg):
            sender = msg.get("sender", "Desconhecido")
            text = msg.get("text", "")
            
            if self.handler.is_monitored(sender):
                print(f"\n📨 {sender}: {text[:100]}")
                
                # Notificar sobre IA disponível
                if self.ai:
                    print("   💡 Use opção 1 para responder com IA")
        
        self.whatsapp.listen(on_message)
    
    def _show_status(self):
        """Mostra status do sistema"""
        print("\n" + "=" * 60)
        print("  📊 STATUS DO SISTEMA")
        print("=" * 60)
        
        # WhatsApp
        wa_status = "✅ Conectado" if self.whatsapp and self.whatsapp.is_connected else "❌ Desconectado"
        print(f"  📱 WhatsApp: {wa_status}")
        
        # IA
        ai_status = "✅ Ativo" if self.ai else "❌ Inativo"
        print(f"  🧠 IA ({self.config.get('provider', 'N/A')}): {ai_status}")
        
        # Cache
        try:
            from src.cache import SemanticCache
            cache = SemanticCache()
            stats = cache.stats()
            print(f"  📦 Cache: {stats.get('active_entries', 0)} entradas")
        except:
            print("  📦 Cache: ❌ Indisponível")
        
        # Database
        db_status = "✅ Conectado" if self.db else "❌ Desconectado"
        print(f"  💾 Database: {db_status}")
        
        # Monitoramento
        print(f"  👁️ Monitorados: {len(self.handler.monitored_contacts)} contatos")
        
        print("=" * 60)
    
    def _add_monitored(self):
        """Adiciona contato ao monitoramento"""
        print("\n👁️ Contatos monitorados atuais:")
        
        if self.handler.monitored_contacts:
            for c in self.handler.monitored_contacts:
                print(f"   • {c}")
        else:
            print("   Nenhum")
        
        contact = input("\n📱 Contato para adicionar (ou 'r' para remover): ").strip()
        
        if contact.lower() == "r":
            to_remove = input("📱 Contato para remover: ").strip()
            self.handler.remove_monitored(to_remove)
            print(f"✅ {to_remove} removido")
        elif contact:
            self.handler.add_monitored(contact)
            print(f"✅ {contact} adicionado")
    
    def _configure_profile(self):
        """Configura perfil de contato"""
        contact = input("📱 Nome do contato: ").strip()
        if not contact:
            return
        
        print("\n📝 Tipos de perfil:")
        print("  1. 💕 Namorada")
        print("  2. 👨‍👩‍👧 Família")
        print("  3. 💼 Trabalho")
        print("  4. 🤝 Amigo")
        print("  5. ⚙️ Personalizado")
        
        choice = input("\n👉 Escolha: ").strip()
        
        type_map = {
            "1": ContactType.NAMORADA,
            "2": ContactType.FAMILIA,
            "3": ContactType.TRABALHO,
            "4": ContactType.AMIGO,
        }
        
        contact_type = type_map.get(choice, ContactType.AMIGO)
        
        # Criar perfil
        profile = ContactProfile(
            name=contact,
            contact_type=contact_type
        )
        
        # Configurações extras para personalizado
        if choice == "5":
            profile.tone = input("Tom (casual/formal/carinhoso): ").strip() or "casual"
            profile.emoji_frequency = input("Emojis (nenhum/pouco/moderado/muito): ").strip() or "moderado"
            profile.context = input("Contexto (ex: 'Minha namorada, gosta de gatos'): ").strip()
            profile.custom_instructions = input("Instruções especiais: ").strip()
        
        self.handler.add_profile(profile)
        
        # Salvar no banco
        if self.db:
            self.db.save_contact_profile(profile.to_dict())
        
        print(f"\n✅ Perfil configurado: {contact} ({contact_type.value})")
    
    def _reconnect(self):
        """Reconecta ao WhatsApp"""
        print("\n🔄 Reconectando...")
        
        if self.whatsapp:
            self.whatsapp.disconnect()
        
        self.whatsapp = WhatsAppClient()
        
        if self.whatsapp.connect():
            print("✅ Reconectado!")
        else:
            print("❌ Falha ao reconectar")
    
    def _exit(self):
        """Encerra o aplicativo"""
        print("\n👋 Encerrando JARVIS...")
        
        if self.whatsapp:
            self.whatsapp.disconnect()
        
        print("✅ Até logo!")


def main():
    """Entry point"""
    app = JarvisWhatsApp()
    app.run()


if __name__ == "__main__":
    main()
