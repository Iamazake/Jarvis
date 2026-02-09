# -*- coding: utf-8 -*-
"""
JARVIS MCP Test Suite
Testa todos os MCP Servers

Autor: JARVIS Team
Versão: 3.0.0
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Cores
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

async def test_mcp_servers():
    """Testa todos os MCP Servers"""
    print(f"\n{BOLD}🧪 JARVIS MCP Test Suite{RESET}\n")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    # === TEST 1: Import MCP Client ===
    print("\n1️⃣ Importando MCP Client...")
    try:
        from core.mcp_client import create_mcp_client
        print(f"   {GREEN}✅ Import OK{RESET}")
        passed += 1
    except Exception as e:
        print(f"   {RED}❌ Erro: {e}{RESET}")
        failed += 1
        return
    
    # === TEST 2: Inicializar MCP ===
    print("\n2️⃣ Inicializando MCP Client...")
    try:
        client = await create_mcp_client()
        print(f"   {GREEN}✅ MCP Client pronto{RESET}")
        print(f"   📊 {len(client.all_tools)} ferramentas carregadas")
        print(f"   🔧 Servers: {list(client.servers.keys())}")
        passed += 1
    except Exception as e:
        print(f"   {RED}❌ Erro: {e}{RESET}")
        failed += 1
        return
    
    # === TEST 3: Tools Server ===
    print("\n3️⃣ Testando Tools Server...")
    try:
        result = await client.call_tool('get_system_info', {})
        if 'sistema' in result.lower() or 'windows' in result.lower():
            print(f"   {GREEN}✅ get_system_info OK{RESET}")
            passed += 1
        else:
            print(f"   {YELLOW}⚠️ Resultado inesperado{RESET}")
            failed += 1
    except Exception as e:
        print(f"   {RED}❌ Erro: {e}{RESET}")
        failed += 1
    
    # === TEST 4: Memory Server ===
    print("\n4️⃣ Testando Memory Server...")
    try:
        # Testa get_identity
        result = await client.call_tool('get_identity', {})
        if 'jarvis' in result.lower():
            print(f"   {GREEN}✅ get_identity OK{RESET}")
            passed += 1
        else:
            print(f"   {YELLOW}⚠️ Resultado: {result[:100]}{RESET}")
            failed += 1
            
        # Testa remember/recall
        await client.call_tool('remember', {'key': 'teste_mcp', 'value': 'funcionando!'})
        recall = await client.call_tool('recall', {'key': 'teste_mcp'})
        if 'funcionando' in recall:
            print(f"   {GREEN}✅ remember/recall OK{RESET}")
            passed += 1
        else:
            print(f"   {YELLOW}⚠️ Recall falhou{RESET}")
            failed += 1
        
        # Limpa teste
        await client.call_tool('forget', {'key': 'teste_mcp'})
        
    except Exception as e:
        print(f"   {RED}❌ Erro: {e}{RESET}")
        failed += 1
    
    # === TEST 5: Search Server ===
    print("\n5️⃣ Testando Search Server...")
    try:
        result = await client.call_tool('get_datetime', {})
        if '202' in result:  # Ano 202x
            print(f"   {GREEN}✅ get_datetime OK{RESET}")
            passed += 1
        else:
            print(f"   {YELLOW}⚠️ Resultado: {result}{RESET}")
            failed += 1
            
        result = await client.call_tool('calculate', {'expression': '2 + 2'})
        if '4' in result:
            print(f"   {GREEN}✅ calculate OK{RESET}")
            passed += 1
        else:
            print(f"   {YELLOW}⚠️ Resultado: {result}{RESET}")
            failed += 1
            
    except Exception as e:
        print(f"   {RED}❌ Erro: {e}{RESET}")
        failed += 1
    
    # === TEST 6: OpenAI Format ===
    print("\n6️⃣ Testando formato OpenAI...")
    try:
        tools = client.get_tools_for_openai()
        if tools and 'function' in tools[0]:
            print(f"   {GREEN}✅ Formato OpenAI OK ({len(tools)} tools){RESET}")
            passed += 1
        else:
            print(f"   {YELLOW}⚠️ Formato incorreto{RESET}")
            failed += 1
    except Exception as e:
        print(f"   {RED}❌ Erro: {e}{RESET}")
        failed += 1
    
    # === TEST 7: AI Engine ===
    print("\n7️⃣ Testando AI Engine...")
    try:
        from core.ai_engine import get_ai
        ai = get_ai(client)
        if ai.client:
            print(f"   {GREEN}✅ AI Engine conectado (modelo: {ai.model}){RESET}")
            passed += 1
        else:
            print(f"   {YELLOW}⚠️ AI sem API key{RESET}")
            failed += 1
    except Exception as e:
        print(f"   {RED}❌ Erro: {e}{RESET}")
        failed += 1
    
    # === Cleanup ===
    await client.stop()
    
    # === RESULTADO ===
    print("\n" + "=" * 50)
    total = passed + failed
    print(f"\n{BOLD}📊 Resultado: {passed}/{total} testes passaram{RESET}")
    
    if failed == 0:
        print(f"\n{GREEN}{BOLD}🎉 TODOS OS TESTES PASSARAM!{RESET}")
        print(f"{GREEN}O JARVIS MCP está pronto para uso.{RESET}")
        print(f"\n{BOLD}Para iniciar:{RESET}")
        print(f"  python jarvis.py --mcp\n")
    else:
        print(f"\n{YELLOW}⚠️ Alguns testes falharam.{RESET}")
    
    return failed == 0


if __name__ == '__main__':
    success = asyncio.run(test_mcp_servers())
    sys.exit(0 if success else 1)
