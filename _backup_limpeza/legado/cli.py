#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS CLI - Interface Interativa
Menu estilo antigo que funciona com Baileys

Autor: JARVIS Team
Versão: 4.1.0
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
import logging
from difflib import SequenceMatcher

# Adicionar src ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Configurar logging (silencioso no CLI)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# URLs dos serviços
WHATSAPP_API = "http://localhost:3001"
JARVIS_API = "http://localhost:5000"

# Arquivo de contatos
CONTACTS_FILE = BASE_DIR / "config" / "contacts.json"

# Cores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def clear():
    """Limpa terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')


def load_contacts() -> dict:
    """Carrega lista de contatos salvos"""
    if CONTACTS_FILE.exists():
        with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_contacts(contacts: dict):
    """Salva lista de contatos"""
    CONTACTS_FILE.parent.mkdir(exist_ok=True)
    with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(contacts, f, indent=2, ensure_ascii=False)


def similarity(a: str, b: str) -> float:
    """Calcula similaridade entre duas strings (0-1)"""
    a = a.lower().strip()
    b = b.lower().strip()
    return SequenceMatcher(None, a, b).ratio()


def find_contact(query: str, min_score: float = 0.4) -> list:
    """
    Busca contato por nome - primeiro no WhatsApp, depois local.
    Retorna lista de matches [(nome, numero, score), ...]
    """
    # Primeiro tenta buscar nos contatos do WhatsApp
    try:
        r = requests.get(f"{WHATSAPP_API}/contacts/search", params={"q": query}, timeout=5)
        if r.ok:
            data = r.json()
            if data.get('success') and data.get('contact'):
                c = data['contact']
                name = c.get('name') or c.get('pushName') or c.get('number')
                return [(name, c.get('number'), c.get('score', 1.0))]
    except:
        pass
    
    # Fallback para busca local
    contacts = load_contacts()
    matches = []
    
    query_lower = query.lower().strip()
    
    for number, info in contacts.items():
        name = info.get('name', '').lower()
        
        # Busca exata primeiro
        if query_lower == name:
            matches.append((info.get('name'), number, 1.0))
            continue
        
        # Busca por substring
        if query_lower in name or name in query_lower:
            score = 0.9
            matches.append((info.get('name'), number, score))
            continue
        
        # Busca por similaridade
        score = similarity(query_lower, name)
        
        # Também verifica partes do nome
        name_parts = name.split()
        for part in name_parts:
            part_score = similarity(query_lower, part)
            if part_score > score:
                score = part_score
        
        if score >= min_score:
            matches.append((info.get('name'), number, score))
    
    # Ordena por score decrescente
    matches.sort(key=lambda x: x[2], reverse=True)
    return matches[:5]  # Top 5


def send_message_by_name(name: str, message: str) -> dict:
    """Envia mensagem buscando contato pelo nome"""
    try:
        r = requests.post(
            f"{WHATSAPP_API}/send-by-name",
            json={"name": name, "message": message},
            timeout=15
        )
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_whatsapp_contacts() -> dict:
    """Busca todos os contatos do WhatsApp"""
    try:
        r = requests.get(f"{WHATSAPP_API}/contacts", timeout=10)
        if r.ok:
            return r.json().get('contacts', {})
    except:
        pass
    return {}


def add_contact(name: str, number: str, context: str = ""):
    """Adiciona/atualiza contato"""
    contacts = load_contacts()
    number = ''.join(filter(str.isdigit, number))
    contacts[number] = {
        'name': name,
        'context': context,
        'added': datetime.now().isoformat()
    }
    save_contacts(contacts)


def check_services() -> dict:
    """Verifica status dos serviços"""
    status = {
        'whatsapp': False,
        'api': False,
        'connected': False
    }
    
    try:
        r = requests.get(f"{WHATSAPP_API}/status", timeout=2)
        if r.ok:
            data = r.json()
            status['whatsapp'] = True
            status['connected'] = data.get('connected', False)
    except:
        pass
    
    try:
        r = requests.get(f"{JARVIS_API}/health", timeout=2)
        status['api'] = r.ok
    except:
        pass
    
    return status


def send_message(to: str, message: str) -> bool:
    """Envia mensagem via WhatsApp"""
    try:
        r = requests.post(
            f"{WHATSAPP_API}/send",
            json={"to": to, "message": message},
            timeout=10
        )
        return r.ok and r.json().get('success', False)
    except Exception as e:
        print(f"{Colors.RED}❌ Erro: {e}{Colors.END}")
        return False


def process_with_ai(message: str, sender: str = "user") -> str:
    """Processa mensagem com IA (pode executar ações)"""
    try:
        r = requests.post(
            f"{JARVIS_API}/process",
            json={"message": message, "sender": sender},
            timeout=30
        )
        if r.ok:
            data = r.json()
            return data.get('response', '')
    except:
        pass
    return ""


def generate_message(prompt: str, context: str = "") -> str:
    """Gera apenas texto com IA (sem executar ações)"""
    try:
        r = requests.post(
            f"{JARVIS_API}/generate",
            json={"prompt": prompt, "context": context},
            timeout=30
        )
        if r.ok:
            data = r.json()
            if data.get('success'):
                return data.get('response', '')
    except Exception as e:
        print(f"{Colors.RED}❌ Erro na IA: {e}{Colors.END}")
    return ""


def load_profiles() -> dict:
    """Carrega perfis do config"""
    profiles_file = BASE_DIR / "config" / "profiles.json"
    if profiles_file.exists():
        with open(profiles_file) as f:
            return json.load(f)
    return {}


def save_profiles(profiles: dict):
    """Salva perfis no config"""
    profiles_file = BASE_DIR / "config" / "profiles.json"
    profiles_file.parent.mkdir(exist_ok=True)
    with open(profiles_file, 'w') as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)


def load_monitors_config() -> dict:
    """Carrega config dos monitors"""
    monitors_file = BASE_DIR / "config" / "monitors.json"
    if monitors_file.exists():
        with open(monitors_file) as f:
            return json.load(f)
    return {}


def save_monitors_config(config: dict):
    """Salva config dos monitors"""
    monitors_file = BASE_DIR / "config" / "monitors.json"
    with open(monitors_file, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


class JarvisCLI:
    """Interface de linha de comando do JARVIS"""
    
    def __init__(self):
        self.profiles = load_profiles()
        self.monitored = []
        self.running = True
    
    def banner(self):
        """Exibe banner"""
        clear()
        print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════╗
║                                                               ║
║   {Colors.BOLD}🤖 JARVIS WhatsApp v4.1{Colors.END}{Colors.CYAN}                                  ║
║   {Colors.GREEN}Baileys + Cache FAISS + IA{Colors.END}{Colors.CYAN}                              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.END}

  📅 {datetime.now():%d/%m/%Y %H:%M}
""")
        
        # Status dos serviços
        status = check_services()
        
        wa_icon = "✅" if status['connected'] else ("⏳" if status['whatsapp'] else "❌")
        wa_text = "Conectado" if status['connected'] else ("Aguardando QR" if status['whatsapp'] else "Offline")
        
        api_icon = "✅" if status['api'] else "❌"
        api_text = "Online" if status['api'] else "Offline"
        
        print(f"  📱 WhatsApp: {wa_icon} {wa_text}")
        print(f"  🤖 API:      {api_icon} {api_text}")
        print()
    
    def menu(self):
        """Menu principal"""
        print(f"""
{Colors.BOLD}═══════════════════════════════════════════════════════════════{Colors.END}
  {Colors.CYAN}📱 MENU PRINCIPAL{Colors.END}
{Colors.BOLD}═══════════════════════════════════════════════════════════════{Colors.END}
  1. 📤 Enviar mensagem (com IA)
  2. 💬 Enviar mensagem direta
  3. 📊 Status do sistema
  4. 👁️  Configurar monitoramento
  5. 👤 Configurar perfil de contato
  6. 🔑 Gerenciar keywords
  7. 📱 Ver contatos monitorados
  8. 🔄 Verificar conexão
  9. 📒 Gerenciar contatos
  0. 🚪 Sair
{Colors.BOLD}═══════════════════════════════════════════════════════════════{Colors.END}
""")
    
    def run(self):
        """Loop principal"""
        while self.running:
            self.banner()
            self.menu()
            
            choice = input(f"\n{Colors.YELLOW}👉 Escolha: {Colors.END}").strip()
            
            actions = {
                "0": self.exit,
                "1": self.send_with_ai,
                "2": self.send_direct,
                "3": self.show_status,
                "4": self.configure_monitors,
                "5": self.configure_profile,
                "6": self.manage_keywords,
                "7": self.show_monitored,
                "8": self.check_connection,
                "9": self.manage_contacts,
            }
            
            action = actions.get(choice)
            if action:
                try:
                    action()
                except KeyboardInterrupt:
                    print("\n")
                except Exception as e:
                    print(f"\n{Colors.RED}❌ Erro: {e}{Colors.END}")
                
                if choice != "0":
                    input(f"\n{Colors.CYAN}Pressione Enter para continuar...{Colors.END}")
            else:
                print(f"\n{Colors.RED}❌ Opção inválida{Colors.END}")
                input()
    
    def send_with_ai(self):
        """Envia mensagem usando IA - busca contato automaticamente"""
        print(f"\n{Colors.CYAN}📤 ENVIAR MENSAGEM (COM IA){Colors.END}\n")
        
        # Busca direta pelo nome - sem precisar cadastrar
        query = input("👤 Para quem? (nome do contato): ").strip()
        if not query:
            return
        
        # Primeiro verifica se parece número
        digits = ''.join(filter(str.isdigit, query))
        if len(digits) >= 10:
            # É número direto - salva com o nome se não existir
            number = digits
            name = digits
            
            # Verificar se já conhece
            contacts = load_contacts()
            if number not in contacts:
                save_name = input(f"{Colors.YELLOW}📝 Nome para salvar este contato: {Colors.END}").strip()
                if save_name:
                    add_contact(save_name, number)
                    # Também adiciona ao WhatsApp
                    try:
                        requests.post(f"{WHATSAPP_API}/contacts/add", 
                                      json={"number": number, "name": save_name}, timeout=5)
                    except:
                        pass
                    name = save_name
                    print(f"{Colors.GREEN}✅ Contato '{save_name}' salvo!{Colors.END}")
            else:
                name = contacts[number].get('name', number)
        else:
            # Busca pelo nome no WhatsApp e localmente
            print(f"\n{Colors.CYAN}🔍 Buscando '{query}' nos contatos...{Colors.END}")
            
            matches = find_contact(query)
            
            if not matches:
                # NÃO ENCONTROU - perguntar número e salvar
                print(f"{Colors.YELLOW}📱 Contato '{query}' não encontrado nos registros.{Colors.END}")
                print(f"{Colors.CYAN}💡 Vou salvar para você não precisar digitar de novo!{Colors.END}\n")
                
                number = input(f"📞 Qual o número de {query}? (com DDD): ").strip()
                number = ''.join(filter(str.isdigit, number))
                
                if not number or len(number) < 10:
                    print(f"{Colors.RED}❌ Número inválido{Colors.END}")
                    return
                
                # Salvar o contato localmente
                add_contact(query, number)
                
                # Salvar no WhatsApp também
                try:
                    requests.post(f"{WHATSAPP_API}/contacts/add", 
                                  json={"number": number, "name": query}, timeout=5)
                except:
                    pass
                
                name = query
                print(f"{Colors.GREEN}✅ Contato '{query}' salvo! Na próxima vez basta digitar o nome.{Colors.END}")
            
            elif len(matches) == 1 or matches[0][2] > 0.8:
                # Match confiável
                name, number, score = matches[0]
                print(f"{Colors.GREEN}✅ Encontrado: {name}{Colors.END}")
            else:
                # Múltiplos matches
                print(f"\n{Colors.CYAN}Encontrados:{Colors.END}")
                for i, (n, num, score) in enumerate(matches, 1):
                    print(f"   {i}. {n} ({int(score*100)}%)")
                print("   0. Cancelar")
                
                choice = input(f"\n{Colors.YELLOW}👉 Qual? {Colors.END}").strip()
                try:
                    idx = int(choice)
                    if idx == 0:
                        return
                    name, number, _ = matches[idx - 1]
                except:
                    print(f"{Colors.RED}❌ Opção inválida{Colors.END}")
                    return
        
        # Verificar perfil local (opcional)
        profile = self.profiles.get(number, {})
        
        print(f"\n💭 O que você quer dizer para {name}?")
        instruction = input("   → ").strip()
        
        if not instruction:
            print(f"{Colors.RED}❌ Instrução vazia{Colors.END}")
            return
        
        # Gerar com IA (usando endpoint /generate que só gera texto)
        print(f"\n{Colors.CYAN}🤖 Gerando mensagem...{Colors.END}")
        
        # Montar prompt com contexto
        context = ""
        if profile:
            profile_type = profile.get('type', 'amigo')
            profile_context = profile.get('context', '')
            context = f"Relacionamento: {profile_type}. {profile_context}"
        
        prompt = f"Escreva uma mensagem para {name}. Intenção do usuário: {instruction}"
        
        response = generate_message(prompt, context)
        
        if response:
            print(f"\n{Colors.GREEN}💬 Mensagem gerada:{Colors.END}")
            print(f"   {response}")
            
            confirm = input(f"\n{Colors.YELLOW}✅ Enviar para {name}? (s/n/e para editar): {Colors.END}").strip().lower()
            
            if confirm == "e":
                response = input("📝 Nova mensagem: ").strip()
                confirm = "s"
            
            if confirm == "s" and response:
                if send_message(number, response):
                    print(f"\n{Colors.GREEN}✅ Mensagem enviada para {name}!{Colors.END}")
                else:
                    print(f"\n{Colors.RED}❌ Falha ao enviar{Colors.END}")
            else:
                print(f"\n{Colors.YELLOW}❌ Cancelado{Colors.END}")
        else:
            print(f"\n{Colors.RED}❌ Não foi possível gerar resposta (API offline?){Colors.END}")
    
    def _resolve_contact(self, query: str):
        """
        Resolve contato por nome ou número.
        Se não encontrar, pergunta o número e salva automaticamente.
        Retorna (numero, nome) ou None
        """
        # Se parece com número, usa direto
        digits = ''.join(filter(str.isdigit, query))
        if len(digits) >= 10:
            # É um número
            contacts = load_contacts()
            info = contacts.get(digits, {})
            name = info.get('name', digits)
            
            # Se não conhece, pergunta se quer salvar
            if digits not in contacts:
                print(f"\n{Colors.YELLOW}📱 Novo contato: {digits}{Colors.END}")
                save_name = input("   Nome para salvar (Enter para pular): ").strip()
                if save_name:
                    add_contact(save_name, digits)
                    # Também salva no WhatsApp
                    try:
                        requests.post(f"{WHATSAPP_API}/contacts/add", 
                                      json={"number": digits, "name": save_name}, timeout=5)
                    except:
                        pass
                    name = save_name
                    print(f"   {Colors.GREEN}✅ Contato salvo!{Colors.END}")
            
            return (digits, name)
        
        # Busca por nome
        matches = find_contact(query)
        
        if not matches:
            # NÃO ENCONTROU - perguntar número e salvar automaticamente
            print(f"\n{Colors.YELLOW}📱 Contato '{query}' não encontrado.{Colors.END}")
            print(f"{Colors.CYAN}💡 Vou salvar para você!{Colors.END}\n")
            
            number = input(f"📞 Qual o número de {query}? (com DDD): ").strip()
            number = ''.join(filter(str.isdigit, number))
            
            if not number or len(number) < 10:
                print(f"{Colors.RED}❌ Número inválido ou cancelado{Colors.END}")
                return None
            
            # Salvar automaticamente
            add_contact(query, number)
            try:
                requests.post(f"{WHATSAPP_API}/contacts/add", 
                              json={"number": number, "name": query}, timeout=5)
            except:
                pass
            
            print(f"{Colors.GREEN}✅ '{query}' salvo! Próxima vez basta digitar o nome.{Colors.END}")
            return (number, query)
        
        if len(matches) == 1 and matches[0][2] > 0.6:
            # Match único e razoavelmente confiável
            name, number, score = matches[0]
            print(f"\n{Colors.GREEN}✅ Encontrado: {name} ({number}){Colors.END}")
            return (number, name)
        
        # Múltiplos matches - deixa escolher
        print(f"\n{Colors.CYAN}🔍 Contatos encontrados:{Colors.END}")
        for i, (name, number, score) in enumerate(matches, 1):
            percent = int(score * 100)
            print(f"   {i}. {name} ({number}) - {percent}% match")
        
        print(f"   0. Cancelar")
        
        choice = input(f"\n{Colors.YELLOW}👉 Escolha: {Colors.END}").strip()
        
        try:
            idx = int(choice)
            if idx == 0:
                return None
            if 1 <= idx <= len(matches):
                name, number, _ = matches[idx - 1]
                return (number, name)
        except:
            pass
        
        print(f"{Colors.RED}❌ Opção inválida{Colors.END}")
        return None
    
    def send_direct(self):
        """Envia mensagem diretamente"""
        print(f"\n{Colors.CYAN}💬 ENVIAR MENSAGEM DIRETA{Colors.END}\n")
        
        query = input("👤 Nome ou número: ").strip()
        if not query:
            return
        
        contact = self._resolve_contact(query)
        if not contact:
            return
        
        number, name = contact
        
        message = input("📝 Mensagem: ").strip()
        if not message:
            return
        
        if send_message(number, message):
            print(f"\n{Colors.GREEN}✅ Enviada para {name}!{Colors.END}")
        else:
            print(f"\n{Colors.RED}❌ Falha{Colors.END}")
    
    def show_status(self):
        """Mostra status completo"""
        print(f"\n{Colors.CYAN}📊 STATUS DO SISTEMA{Colors.END}\n")
        
        status = check_services()
        
        print(f"  📱 WhatsApp Service:")
        if status['whatsapp']:
            try:
                r = requests.get(f"{WHATSAPP_API}/status", timeout=2)
                data = r.json()
                print(f"     Status: {'✅ Conectado' if data.get('connected') else '⏳ Aguardando'}")
                print(f"     Uptime: {data.get('uptime', 'N/A')}")
            except:
                print(f"     Status: ❌ Erro ao obter status")
        else:
            print(f"     Status: ❌ Serviço offline")
        
        print(f"\n  🤖 API JARVIS:")
        if status['api']:
            try:
                r = requests.get(f"{JARVIS_API}/stats", timeout=2)
                data = r.json()
                print(f"     Status: ✅ Online")
                print(f"     Mensagens: {data.get('received', 0)} recebidas")
                print(f"     Processadas: {data.get('processed', 0)}")
                print(f"     Erros: {data.get('errors', 0)}")
            except:
                print(f"     Status: ✅ Online")
        else:
            print(f"     Status: ❌ Offline")
        
        # Monitors
        try:
            config = load_monitors_config()
            print(f"\n  👁️ Monitors:")
            print(f"     Keywords: {'✅' if config.get('keywords', {}).get('enabled') else '❌'} ({len(config.get('keywords', {}).get('words', []))} palavras)")
            print(f"     Contatos: {'✅' if config.get('contacts', {}).get('enabled') else '❌'} ({len(config.get('contacts', {}).get('jids', []))} JIDs)")
            print(f"     Mídia:    {'✅' if config.get('media', {}).get('enabled') else '❌'}")
            print(f"     Presença: {'✅' if config.get('presence', {}).get('enabled') else '❌'}")
        except:
            print(f"\n  👁️ Monitors: ⚠️ Config não encontrada")
    
    def configure_monitors(self):
        """Configura sistema de monitoramento"""
        print(f"\n{Colors.CYAN}👁️ CONFIGURAR MONITORAMENTO{Colors.END}\n")
        
        config = load_monitors_config()
        
        print("  1. Ativar/desativar Keywords")
        print("  2. Ativar/desativar Contatos")
        print("  3. Ativar/desativar Mídia")
        print("  4. Ativar/desativar Presença")
        print("  5. Alterar notificador (seu número)")
        print("  0. Voltar")
        
        choice = input(f"\n{Colors.YELLOW}👉 Escolha: {Colors.END}").strip()
        
        if choice == "1":
            current = config.get('keywords', {}).get('enabled', False)
            config.setdefault('keywords', {})['enabled'] = not current
            print(f"Keywords: {'✅ Ativado' if not current else '❌ Desativado'}")
        elif choice == "2":
            current = config.get('contacts', {}).get('enabled', False)
            config.setdefault('contacts', {})['enabled'] = not current
            print(f"Contatos: {'✅ Ativado' if not current else '❌ Desativado'}")
        elif choice == "3":
            current = config.get('media', {}).get('enabled', False)
            config.setdefault('media', {})['enabled'] = not current
            print(f"Mídia: {'✅ Ativado' if not current else '❌ Desativado'}")
        elif choice == "4":
            current = config.get('presence', {}).get('enabled', False)
            config.setdefault('presence', {})['enabled'] = not current
            print(f"Presença: {'✅ Ativado' if not current else '❌ Desativado'}")
        elif choice == "5":
            number = input("📱 Seu número (para receber notificações): ").strip()
            number = ''.join(filter(str.isdigit, number))
            if number:
                config['notifier'] = f"{number}@s.whatsapp.net"
                print(f"✅ Notificador: {number}")
        else:
            return
        
        save_monitors_config(config)
        print(f"\n{Colors.GREEN}✅ Configuração salva!{Colors.END}")
    
    def configure_profile(self):
        """Configura perfil de contato"""
        print(f"\n{Colors.CYAN}👤 CONFIGURAR PERFIL{Colors.END}\n")
        
        contact = input("📱 Número do contato: ").strip()
        contact = ''.join(filter(str.isdigit, contact))
        if not contact:
            return
        
        print("\n📝 Tipos de perfil:")
        print("  1. 💕 Namorada(o)")
        print("  2. 👨‍👩‍👧 Família")
        print("  3. 💼 Trabalho")
        print("  4. 🤝 Amigo")
        
        choice = input(f"\n{Colors.YELLOW}👉 Escolha: {Colors.END}").strip()
        
        type_map = {"1": "namorada", "2": "familia", "3": "trabalho", "4": "amigo"}
        profile_type = type_map.get(choice, "amigo")
        
        name = input("👤 Nome do contato: ").strip() or contact
        context = input("📝 Contexto (ex: 'Gosta de gatinhos'): ").strip()
        
        self.profiles[contact] = {
            "name": name,
            "type": profile_type,
            "context": context
        }
        
        save_profiles(self.profiles)
        
        print(f"\n{Colors.GREEN}✅ Perfil salvo: {name} ({profile_type}){Colors.END}")
    
    def manage_keywords(self):
        """Gerencia keywords de monitoramento"""
        print(f"\n{Colors.CYAN}🔑 GERENCIAR KEYWORDS{Colors.END}\n")
        
        config = load_monitors_config()
        keywords = config.get('keywords', {}).get('words', [])
        
        print("📝 Keywords atuais:")
        for i, kw in enumerate(keywords, 1):
            print(f"   {i}. {kw}")
        
        if not keywords:
            print("   (nenhuma)")
        
        print("\n  1. Adicionar keyword")
        print("  2. Remover keyword")
        print("  0. Voltar")
        
        choice = input(f"\n{Colors.YELLOW}👉 Escolha: {Colors.END}").strip()
        
        if choice == "1":
            kw = input("🔑 Nova keyword: ").strip()
            if kw and kw not in keywords:
                keywords.append(kw)
                config.setdefault('keywords', {})['words'] = keywords
                save_monitors_config(config)
                print(f"{Colors.GREEN}✅ '{kw}' adicionada{Colors.END}")
        elif choice == "2":
            kw = input("🔑 Keyword para remover: ").strip()
            if kw in keywords:
                keywords.remove(kw)
                config['keywords']['words'] = keywords
                save_monitors_config(config)
                print(f"{Colors.GREEN}✅ '{kw}' removida{Colors.END}")
    
    def show_monitored(self):
        """Mostra contatos monitorados"""
        print(f"\n{Colors.CYAN}📱 CONTATOS MONITORADOS{Colors.END}\n")
        
        config = load_monitors_config()
        contacts = config.get('contacts', {}).get('jids', [])
        
        if contacts:
            for c in contacts:
                print(f"   • {c}")
        else:
            print("   (nenhum)")
        
        print("\n  1. Adicionar contato")
        print("  2. Remover contato")
        print("  0. Voltar")
        
        choice = input(f"\n{Colors.YELLOW}👉 Escolha: {Colors.END}").strip()
        
        if choice == "1":
            number = input("📱 Número: ").strip()
            number = ''.join(filter(str.isdigit, number))
            if number:
                jid = f"{number}@s.whatsapp.net"
                if jid not in contacts:
                    contacts.append(jid)
                    config.setdefault('contacts', {})['jids'] = contacts
                    save_monitors_config(config)
                    print(f"{Colors.GREEN}✅ {number} adicionado{Colors.END}")
        elif choice == "2":
            number = input("📱 Número para remover: ").strip()
            number = ''.join(filter(str.isdigit, number))
            jid = f"{number}@s.whatsapp.net"
            if jid in contacts:
                contacts.remove(jid)
                config['contacts']['jids'] = contacts
                save_monitors_config(config)
                print(f"{Colors.GREEN}✅ {number} removido{Colors.END}")
    
    def check_connection(self):
        """Verifica e mostra instrução para conexão"""
        print(f"\n{Colors.CYAN}🔄 VERIFICAR CONEXÃO{Colors.END}\n")
        
        status = check_services()
        
        if not status['whatsapp']:
            print(f"{Colors.RED}❌ Serviço WhatsApp não está rodando!{Colors.END}")
            print(f"\n{Colors.YELLOW}Para iniciar:{Colors.END}")
            print("   cd services/whatsapp && node index.js")
            return
        
        if status['connected']:
            print(f"{Colors.GREEN}✅ WhatsApp está conectado!{Colors.END}")
        else:
            print(f"{Colors.YELLOW}⏳ WhatsApp aguardando QR Code...{Colors.END}")
            print("\nVejas no terminal do serviço WhatsApp para escanear o QR.")
            print("Depois de escanear, volte aqui.")
    
    def manage_contacts(self):
        """Gerencia lista de contatos"""
        print(f"\n{Colors.CYAN}📒 GERENCIAR CONTATOS{Colors.END}\n")
        
        # Buscar contatos do WhatsApp também
        wa_contacts = get_whatsapp_contacts()
        contacts = load_contacts()
        
        total_local = len(contacts)
        total_wa = len(wa_contacts)
        
        print(f"📱 Contatos locais: {total_local}")
        print(f"📲 Contatos WhatsApp: {total_wa}")
        
        if contacts:
            print(f"\n{Colors.CYAN}Locais:{Colors.END}")
            for number, info in list(contacts.items())[:5]:
                name = info.get('name', 'Sem nome')
                print(f"   • {name} ({number})")
            if len(contacts) > 5:
                print(f"   ... e mais {len(contacts) - 5}")
        
        if wa_contacts:
            print(f"\n{Colors.CYAN}WhatsApp (aprendidos):{Colors.END}")
            for number, info in list(wa_contacts.items())[:5]:
                name = info.get('name') or info.get('pushName', 'Sem nome')
                print(f"   • {name} ({number})")
            if len(wa_contacts) > 5:
                print(f"   ... e mais {len(wa_contacts) - 5}")
        
        print(f"""
  1. ➕ Adicionar contato
  2. 🔍 Buscar contato
  3. ❌ Remover contato
  4. 📋 Listar todos
  5. 🔄 Sincronizar WhatsApp → Local
  0. Voltar
""")
        
        choice = input(f"{Colors.YELLOW}👉 Escolha: {Colors.END}").strip()
        
        if choice == "1":
            name = input("👤 Nome: ").strip()
            if not name:
                return
            number = input("📱 Número (com DDD): ").strip()
            number = ''.join(filter(str.isdigit, number))
            if not number or len(number) < 10:
                print(f"{Colors.RED}❌ Número inválido{Colors.END}")
                return
            context = input("📝 Contexto (opcional): ").strip()
            
            add_contact(name, number, context)
            
            # Também adiciona ao WhatsApp
            try:
                requests.post(f"{WHATSAPP_API}/contacts/add", 
                              json={"number": number, "name": name}, timeout=5)
            except:
                pass
            
            print(f"\n{Colors.GREEN}✅ Contato salvo: {name} ({number}){Colors.END}")
            
        elif choice == "2":
            query = input("🔍 Buscar: ").strip()
            if not query:
                return
            
            matches = find_contact(query, min_score=0.3)
            
            if matches:
                print(f"\n{Colors.CYAN}Resultados:{Colors.END}")
                for name, number, score in matches:
                    percent = int(score * 100)
                    print(f"   • {name} ({number}) - {percent}% match")
            else:
                print(f"{Colors.YELLOW}Nenhum contato encontrado{Colors.END}")
                
        elif choice == "3":
            query = input("❌ Nome/número para remover: ").strip()
            
            # Busca
            matches = find_contact(query)
            if matches:
                name, number, _ = matches[0]
                confirm = input(f"Remover {name} ({number})? (s/n): ").strip().lower()
                if confirm == "s":
                    contacts = load_contacts()
                    if number in contacts:
                        del contacts[number]
                        save_contacts(contacts)
                        print(f"{Colors.GREEN}✅ Removido{Colors.END}")
            else:
                print(f"{Colors.YELLOW}Contato não encontrado{Colors.END}")
                
        elif choice == "4":
            print(f"\n{Colors.CYAN}📋 TODOS OS CONTATOS{Colors.END}\n")
            
            # Merge local + WhatsApp
            all_contacts = {}
            for number, info in wa_contacts.items():
                all_contacts[number] = {
                    'name': info.get('name') or info.get('pushName', ''),
                    'source': 'whatsapp'
                }
            for number, info in contacts.items():
                all_contacts[number] = {
                    'name': info.get('name', ''),
                    'context': info.get('context', ''),
                    'source': 'local'
                }
            
            for number, info in all_contacts.items():
                name = info.get('name', 'Sem nome')
                source = info.get('source', '')
                ctx = info.get('context', '')
                icon = "📲" if source == 'whatsapp' else "📱"
                print(f"   {icon} {name}: {number}")
                if ctx:
                    print(f"      └─ {ctx}")
                    
        elif choice == "5":
            # Sincronizar WhatsApp → Local
            print(f"\n{Colors.CYAN}🔄 Sincronizando contatos do WhatsApp...{Colors.END}")
            
            wa_contacts = get_whatsapp_contacts()
            if not wa_contacts:
                print(f"{Colors.YELLOW}Nenhum contato do WhatsApp disponível{Colors.END}")
                return
            
            imported = 0
            for number, info in wa_contacts.items():
                name = info.get('name') or info.get('pushName')
                if name and number not in contacts:
                    add_contact(name, number)
                    imported += 1
            
            print(f"\n{Colors.GREEN}✅ {imported} contatos importados!{Colors.END}")
    
    def exit(self):
        """Sai do CLI"""
        print(f"\n{Colors.CYAN}👋 Até logo!{Colors.END}\n")
        self.running = False


def main():
    """Entry point"""
    cli = JarvisCLI()
    cli.run()


if __name__ == "__main__":
    main()
