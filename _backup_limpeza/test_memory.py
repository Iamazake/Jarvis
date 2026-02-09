# -*- coding: utf-8 -*-
"""
Teste de memória do JARVIS
"""
import asyncio
import sys
sys.path.insert(0, '.')

from core.jarvis import Jarvis

async def main():
    print("=" * 50)
    print("TESTE DE MEMÓRIA DO JARVIS")
    print("=" * 50)
    
    jarvis = Jarvis()
    await jarvis.start()
    
    print("\n=== TESTE 1: Apresentação ===")
    r = await jarvis.process('meu nome é Pedro, eu sou seu criador')
    print(f'R: {r}')
    
    print("\n=== TESTE 2: Verifica memória ===")
    r = await jarvis.process('qual meu nome e quem te criou?')
    print(f'R: {r}')
    
    print("\n=== TESTE 3: Identidade ===")
    r = await jarvis.process('qual seu nome e pra que voce serve?')
    print(f'R: {r}')
    
    await jarvis.stop()
    print("\n" + "=" * 50)
    print("Teste concluído!")

if __name__ == "__main__":
    asyncio.run(main())
