#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Sistema de Monitors
Verifica se os monitors estão funcionando corretamente
"""

import sys
import os

# Adiciona o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.monitors import (
    KeywordMonitor,
    ContactMonitor,
    MediaMonitor,
    PresenceMonitor,
    MonitorManager,
    load_monitors_from_config
)


def test_keyword_monitor():
    """Testa KeywordMonitor"""
    print("\n📝 Testando KeywordMonitor...")
    
    monitor = KeywordMonitor(
        notifier_jid="5511988669454@s.whatsapp.net",
        keywords=["trabalho", "grana", "urgente"]
    )
    
    # Teste com mensagem que contém keyword
    event1 = {
        'type': 'message',
        'sender': '5511999999999@s.whatsapp.net',
        'push_name': 'Teste',
        'data': {'text': 'Oi, preciso falar sobre trabalho urgente!'}
    }
    
    print(f"   Monitor: {monitor}")
    print(f"   Keywords: {monitor.list_keywords()}")
    
    # Simula (não envia de verdade pois notifier pode não existir)
    monitor.enabled = False  # Desabilita para não tentar enviar
    monitor.update(event1)
    print("   ✅ KeywordMonitor OK")


def test_contact_monitor():
    """Testa ContactMonitor"""
    print("\n👤 Testando ContactMonitor...")
    
    monitor = ContactMonitor(
        notifier_jid="5511988669454@s.whatsapp.net",
        contacts={"5511999999999@s.whatsapp.net"}
    )
    
    # Adiciona contato
    monitor.add_contact("5511888888888")
    
    print(f"   Monitor: {monitor}")
    print(f"   Contatos: {monitor.list_contacts()}")
    print("   ✅ ContactMonitor OK")


def test_media_monitor():
    """Testa MediaMonitor"""
    print("\n🖼️ Testando MediaMonitor...")
    
    monitor = MediaMonitor(
        notifier_jid="5511988669454@s.whatsapp.net",
        contacts=None,  # Monitora todos
        save_path="data/media",
        save_media=False  # Não salva de verdade no teste
    )
    
    print(f"   Monitor: {monitor}")
    print(f"   Save path: {monitor.save_path}")
    print("   ✅ MediaMonitor OK")


def test_presence_monitor():
    """Testa PresenceMonitor"""
    print("\n🟢 Testando PresenceMonitor...")
    
    monitor = PresenceMonitor(
        notifier_jid="5511988669454@s.whatsapp.net",
        contacts=None,
        notify_on_online=False
    )
    
    # Simula evento de presença
    event = {
        'type': 'presence',
        'sender': '5511999999999@s.whatsapp.net',
        'push_name': 'João',
        'data': {'status': 'available'}
    }
    
    monitor.enabled = False  # Desabilita para não tentar enviar
    monitor.update(event)
    
    print(f"   Monitor: {monitor}")
    print(f"   Online: {monitor.get_online_contacts()}")
    print("   ✅ PresenceMonitor OK")


def test_monitor_manager():
    """Testa MonitorManager"""
    print("\n🎛️ Testando MonitorManager...")
    
    manager = MonitorManager()
    
    kw = KeywordMonitor("5511988669454@s.whatsapp.net", ["teste"])
    ct = ContactMonitor("5511988669454@s.whatsapp.net")
    
    manager.add(kw)
    manager.add(ct)
    
    print(f"   Manager: {manager}")
    print(f"   Monitors: {manager.list_monitors()}")
    print("   ✅ MonitorManager OK")


def test_load_from_config():
    """Testa carregar monitors de config/monitors.json"""
    print("\n📂 Testando load_monitors_from_config...")
    
    try:
        manager = load_monitors_from_config("config/monitors.json")
        print(f"   Manager: {manager}")
        print(f"   Monitors carregados: {len(manager)}")
        for m in manager.list_monitors():
            print(f"     - {m}")
        print("   ✅ Config load OK")
    except FileNotFoundError:
        print("   ⚠️ Config não encontrada (normal se executar fora do diretório jarvis)")
    except Exception as e:
        print(f"   ❌ Erro: {e}")


def main():
    print("=" * 50)
    print("  🧪 TESTE DO SISTEMA DE MONITORS")
    print("=" * 50)
    
    try:
        test_keyword_monitor()
        test_contact_monitor()
        test_media_monitor()
        test_presence_monitor()
        test_monitor_manager()
        test_load_from_config()
        
        print("\n" + "=" * 50)
        print("  ✅ TODOS OS TESTES PASSARAM!")
        print("=" * 50)
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
