# -*- coding: utf-8 -*-
"""
WhatsApp Client - Selenium com Anti-Detecção
Facade Pattern: Interface unificada para WhatsApp Web

Autor: JARVIS Team
Versão: 4.0.0
"""

import os
import sys
import time
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, List, Callable
from urllib.parse import quote
from pathlib import Path

# Configurar logging
logger = logging.getLogger(__name__)

# Imports Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, 
        NoSuchElementException,
        StaleElementReferenceException,
        WebDriverException
    )
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
    logger.error("❌ Selenium não instalado! Execute: pip install selenium")

# Diretórios
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
PROFILE_DIR = DATA_DIR / "wa_profile"

# XPaths atualizados (fevereiro 2026)
XPATHS = {
    # Indicadores de login
    "chat_list": '//div[@id="pane-side"]',
    "chat_list_alt": '//div[contains(@aria-label, "Lista de conversas")]',
    "chat_list_alt2": '//span[text()="Arquivadas"]',
    "qr_code": '//canvas[@aria-label="Scan this QR code to link a device!"]',
    "qr_code_alt": '//div[@data-ref]',
    
    # Elementos de conversa
    "search_box": '//div[@contenteditable="true"][@data-tab="3"]',
    "chat_item": '//div[@data-testid="cell-frame-container"]',
    "message_input": '//div[@contenteditable="true"][@data-tab="10"]',
    "message_input_alt": '//div[@title="Digite uma mensagem"]',
    "send_button": '//button[@aria-label="Enviar"]',
    "send_button_alt": '//span[@data-icon="send"]',
    
    # Mensagens
    "incoming_messages": '//div[contains(@class, "message-in")]',
    "outgoing_messages": '//div[contains(@class, "message-out")]',
    "message_text": './/span[contains(@class, "selectable-text")]',
    "message_time": './/span[@data-testid="msg-meta"]//span',
    
    # Link wa.me
    "action_button": '//a[@id="action-button"]',
}


class WhatsAppClient:
    """
    Cliente WhatsApp Web com anti-detecção
    
    Singleton Pattern: Uma única instância do Chrome
    Facade Pattern: Interface simplificada
    
    Uso:
        client = WhatsAppClient()
        client.connect()
        client.send_message("5511999999999", "Olá!")
    """
    
    _instance: Optional['WhatsAppClient'] = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton: Garante apenas uma instância"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, profile_dir: Path = None):
        """
        Inicializa o cliente WhatsApp
        
        Args:
            profile_dir: Diretório para salvar sessão do Chrome
        """
        if self._initialized:
            return
            
        self.profile_dir = profile_dir or PROFILE_DIR
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        
        self.driver: Optional[webdriver.Chrome] = None
        self.is_connected: bool = False
        self.message_hashes: set = set()
        
        # Callbacks
        self.on_message: Optional[Callable] = None
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        
        self._initialized = True
        logger.info(f"📁 Profile: {self.profile_dir}")
    
    def connect(self, timeout: int = 120) -> bool:
        """
        Conecta ao WhatsApp Web
        
        Args:
            timeout: Tempo máximo para escanear QR Code
            
        Returns:
            True se conectou com sucesso
        """
        if not HAS_SELENIUM:
            logger.error("❌ Selenium não disponível")
            return False
        
        if not self._start_driver():
            return False
        
        return self._wait_for_login(timeout)
    
    def disconnect(self):
        """Desconecta e fecha o Chrome"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            self.is_connected = False
            logger.info("🔒 Chrome fechado")
            
            if self.on_disconnect:
                self.on_disconnect()
    
    def send_message(self, phone: str, text: str) -> bool:
        """
        Envia mensagem para um número
        
        Args:
            phone: Número com código do país (ex: 5511999999999)
            text: Texto da mensagem
            
        Returns:
            True se enviou com sucesso
        """
        if not self.is_connected:
            logger.warning("⚠️ WhatsApp não conectado")
            return False
        
        # Tentar via link wa.me primeiro (mais confiável)
        if self._send_via_link(phone, text):
            return True
        
        # Fallback: buscar contato
        return self._send_via_search(phone, text)
    
    def open_chat(self, contact: str) -> bool:
        """
        Abre um chat específico
        
        Args:
            contact: Nome ou número do contato
            
        Returns:
            True se abriu o chat
        """
        if not self.is_connected:
            return False
        
        try:
            self.driver.get("https://web.whatsapp.com")
            time.sleep(2)
            
            # Buscar contato
            search = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, XPATHS["search_box"]))
            )
            search.click()
            search.clear()
            search.send_keys(contact)
            time.sleep(2)
            
            # Clicar no resultado
            chat = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, XPATHS["chat_item"]))
            )
            chat.click()
            time.sleep(1)
            
            logger.info(f"✅ Chat aberto: {contact}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao abrir chat: {e}")
            return False
    
    def send_to_current_chat(self, text: str) -> bool:
        """
        Envia mensagem no chat atual
        
        Args:
            text: Texto da mensagem
            
        Returns:
            True se enviou
        """
        if not self.is_connected:
            return False
        
        try:
            # Campo de mensagem
            msg_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, XPATHS["message_input"]))
            )
            msg_input.click()
            
            # Digitar com quebras de linha
            for i, line in enumerate(text.split('\n')):
                msg_input.send_keys(line)
                if i < len(text.split('\n')) - 1:
                    msg_input.send_keys(Keys.SHIFT + Keys.ENTER)
            
            # Enviar
            send_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, XPATHS["send_button"]))
            )
            send_btn.click()
            
            logger.info("✅ Mensagem enviada")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar: {e}")
            return False
    
    def get_new_messages(self) -> List[Dict]:
        """
        Obtém novas mensagens recebidas
        
        Returns:
            Lista de mensagens: [{"sender": str, "text": str, "timestamp": str}]
        """
        if not self.is_connected:
            return []
        
        messages = []
        
        try:
            elements = self.driver.find_elements(By.XPATH, XPATHS["incoming_messages"])
            
            for elem in elements[-20:]:
                try:
                    text_elem = elem.find_element(By.XPATH, XPATHS["message_text"])
                    text = text_elem.text.strip()
                    
                    if not text:
                        continue
                    
                    # Evitar duplicatas
                    msg_hash = hashlib.md5(text.encode()).hexdigest()[:16]
                    if msg_hash in self.message_hashes:
                        continue
                    
                    self.message_hashes.add(msg_hash)
                    
                    messages.append({
                        "sender": "contact",
                        "text": text,
                        "timestamp": datetime.now().isoformat(),
                        "is_incoming": True
                    })
                    
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Erro ao obter mensagens: {e}")
        
        return messages
    
    def get_last_messages(self, count: int = 10) -> List[Dict]:
        """
        Obtém últimas mensagens do chat atual
        
        Args:
            count: Número máximo de mensagens
            
        Returns:
            Lista de mensagens
        """
        if not self.is_connected:
            return []
        
        messages = []
        
        try:
            # Mensagens recebidas
            incoming = self.driver.find_elements(By.XPATH, XPATHS["incoming_messages"])
            for msg in incoming[-count:]:
                try:
                    text = msg.find_element(By.XPATH, XPATHS["message_text"]).text.strip()
                    if text:
                        messages.append({
                            "sender": "contact",
                            "text": text,
                            "is_incoming": True
                        })
                except:
                    pass
            
            # Mensagens enviadas
            outgoing = self.driver.find_elements(By.XPATH, XPATHS["outgoing_messages"])
            for msg in outgoing[-count:]:
                try:
                    text = msg.find_element(By.XPATH, XPATHS["message_text"]).text.strip()
                    if text:
                        messages.append({
                            "sender": "me",
                            "text": text,
                            "is_incoming": False
                        })
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Erro: {e}")
        
        return messages[-count:]
    
    def listen(self, callback: Callable, interval: int = 3):
        """
        Monitora mensagens em loop
        
        Args:
            callback: Função chamada para cada mensagem
            interval: Intervalo entre verificações (segundos)
        """
        logger.info("👂 Iniciando monitoramento de mensagens...")
        
        while self.is_connected:
            try:
                messages = self.get_new_messages()
                
                for msg in messages:
                    if callback:
                        callback(msg)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitoramento interrompido")
                break
            except Exception as e:
                logger.error(f"Erro no listener: {e}")
                time.sleep(5)
    
    # ========== Métodos Privados ==========
    
    def _start_driver(self) -> bool:
        """Inicia o Chrome com anti-detecção"""
        try:
            logger.info("🚀 Iniciando Chrome...")
            
            options = Options()
            options.add_argument(f"--user-data-dir={self.profile_dir}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--window-size=1366,768")
            options.add_argument("--lang=pt-BR")
            
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_experimental_option("prefs", {
                "profile.default_content_setting_values.notifications": 2,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
            })
            
            # Buscar ChromeDriver
            service = self._get_chrome_service()
            if not service:
                return False
            
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Remover detecção de automação
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en'] });
                    window.chrome = { runtime: {} };
                """
            })
            
            self.driver.get("https://web.whatsapp.com")
            logger.info("✅ Chrome iniciado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar Chrome: {e}")
            return False
    
    def _get_chrome_service(self) -> Optional[Service]:
        """Obtém o serviço do ChromeDriver"""
        paths = [
            "/usr/local/bin/chromedriver",
            "/opt/homebrew/bin/chromedriver",
            "/usr/bin/chromedriver",
        ]
        
        for path in paths:
            if os.path.exists(path):
                logger.info(f"📂 ChromeDriver: {path}")
                return Service(path)
        
        # Tentar webdriver-manager
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            logger.info("⬇️ Baixando ChromeDriver...")
            return Service(ChromeDriverManager().install())
        except Exception as e:
            logger.error(f"❌ ChromeDriver não encontrado: {e}")
            return None
    
    def _wait_for_login(self, timeout: int) -> bool:
        """Aguarda login no WhatsApp"""
        logger.info("📱 Aguardando login... (escaneie o QR Code se necessário)")
        
        start = time.time()
        
        while time.time() - start < timeout:
            try:
                # Verificar se logou
                if self._is_logged_in():
                    self.is_connected = True
                    logger.info("✅ WhatsApp conectado!")
                    
                    if self.on_connect:
                        self.on_connect()
                    
                    return True
                
                time.sleep(2)
                
            except Exception as e:
                logger.debug(f"Aguardando: {e}")
                time.sleep(1)
        
        logger.error("❌ Timeout - QR Code não escaneado")
        return False
    
    def _is_logged_in(self) -> bool:
        """Verifica se está logado"""
        if not self.driver:
            return False
        
        try:
            # Tentar múltiplos seletores
            for key in ["chat_list", "chat_list_alt", "chat_list_alt2"]:
                elements = self.driver.find_elements(By.XPATH, XPATHS[key])
                if elements:
                    return True
            
            # Tentar pelo ID
            try:
                self.driver.find_element(By.ID, "pane-side")
                return True
            except:
                pass
                
        except:
            pass
        
        return False
    
    def _send_via_link(self, phone: str, text: str) -> bool:
        """Envia via link wa.me"""
        try:
            encoded = quote(text)
            self.driver.get(f"https://wa.me/{phone}?text={encoded}")
            time.sleep(2)
            
            # Clicar em "Enviar"
            try:
                btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, XPATHS["action_button"]))
                )
                btn.click()
                time.sleep(2)
            except:
                pass
            
            # Enviar
            send = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, XPATHS["send_button"]))
            )
            send.click()
            
            logger.info(f"✅ Mensagem enviada para {phone}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro via link: {e}")
            return False
    
    def _send_via_search(self, phone: str, text: str) -> bool:
        """Envia buscando o contato"""
        try:
            self.driver.get("https://web.whatsapp.com")
            time.sleep(3)
            
            # Buscar
            search = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, XPATHS["search_box"]))
            )
            search.click()
            search.send_keys(phone)
            time.sleep(2)
            
            # Clicar no resultado
            chat = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, XPATHS["chat_item"]))
            )
            chat.click()
            time.sleep(1)
            
            # Digitar e enviar
            msg_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, XPATHS["message_input"]))
            )
            msg_input.click()
            msg_input.send_keys(text)
            
            send = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, XPATHS["send_button"]))
            )
            send.click()
            
            logger.info(f"✅ Mensagem enviada para {phone}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro via busca: {e}")
            return False


# Alias para compatibilidade
UndetectedWhatsApp = WhatsAppClient
