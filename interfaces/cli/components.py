# -*- coding: utf-8 -*-
"""
CLI Components - Componentes visuais do CLI
"""

import os
import sys
import asyncio
from typing import List


class Colors:
    """Cores ANSI para terminal"""
    # Cores básicas
    BLACK = '\033[30m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    # Estilos
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    
    # Reset
    END = '\033[0m'
    
    @classmethod
    def disable(cls):
        """Desativa cores (para terminais sem suporte)"""
        for attr in dir(cls):
            if not attr.startswith('_') and attr != 'disable':
                setattr(cls, attr, '')


def clear_screen():
    """Limpa a tela do terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str):
    """Imprime header estilizado"""
    width = 60
    
    print(f"{Colors.CYAN}{'═' * width}{Colors.END}")
    print(f"{Colors.CYAN}║{Colors.END} {Colors.BOLD}🤖 {title:^{width-6}}{Colors.END} {Colors.CYAN}║{Colors.END}")
    print(f"{Colors.CYAN}{'═' * width}{Colors.END}")
    
    # Linha de status
    from datetime import datetime
    now = datetime.now().strftime("%H:%M")
    status = f"🟢 Online | ⏰ {now}"
    print(f"{Colors.DIM}{status:^{width}}{Colors.END}")
    print()


def print_box(title: str, lines: List[str], color: str = Colors.CYAN):
    """Imprime box com título e conteúdo"""
    width = max(len(title) + 4, max(len(line) for line in lines) + 4) if lines else len(title) + 4
    width = max(width, 40)
    
    print(f"\n{color}┌{'─' * (width-2)}┐{Colors.END}")
    print(f"{color}│{Colors.END} {Colors.BOLD}{title}{Colors.END}{' ' * (width - len(title) - 3)}{color}│{Colors.END}")
    print(f"{color}├{'─' * (width-2)}┤{Colors.END}")
    
    for line in lines:
        padding = width - len(line) - 3
        print(f"{color}│{Colors.END} {line}{' ' * padding}{color}│{Colors.END}")
    
    print(f"{color}└{'─' * (width-2)}┘{Colors.END}")


async def print_typing(text: str, delay: float = 0.01):
    """Imprime texto com efeito de digitação"""
    for char in text:
        print(char, end='', flush=True)
        
        # Pequena pausa entre caracteres
        if delay > 0:
            await asyncio.sleep(delay)
    
    print()  # Nova linha no final


def print_progress(current: int, total: int, prefix: str = "", suffix: str = "", width: int = 40):
    """Imprime barra de progresso"""
    percent = current / total
    filled = int(width * percent)
    bar = '█' * filled + '░' * (width - filled)
    
    print(f"\r{prefix} [{Colors.GREEN}{bar}{Colors.END}] {percent*100:.1f}% {suffix}", end='', flush=True)
    
    if current >= total:
        print()


def print_table(headers: List[str], rows: List[List[str]]):
    """Imprime tabela formatada"""
    # Calcula larguras
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    
    # Header
    header_line = " │ ".join(f"{h:^{widths[i]}}" for i, h in enumerate(headers))
    separator = "─┼─".join("─" * w for w in widths)
    
    print(f"\n{Colors.BOLD}{header_line}{Colors.END}")
    print(separator)
    
    # Rows
    for row in rows:
        row_line = " │ ".join(f"{str(cell):<{widths[i]}}" for i, cell in enumerate(row))
        print(row_line)
    
    print()


def print_list(items: List[str], numbered: bool = False, bullet: str = "•"):
    """Imprime lista formatada"""
    for i, item in enumerate(items, 1):
        if numbered:
            print(f"  {Colors.CYAN}{i}.{Colors.END} {item}")
        else:
            print(f"  {Colors.CYAN}{bullet}{Colors.END} {item}")


def print_error(message: str):
    """Imprime mensagem de erro"""
    print(f"{Colors.RED}❌ Erro: {message}{Colors.END}")


def print_success(message: str):
    """Imprime mensagem de sucesso"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_warning(message: str):
    """Imprime aviso"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


def print_info(message: str):
    """Imprime informação"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")
