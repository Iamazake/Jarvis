# -*- coding: utf-8 -*-
"""
System Info - Informações do Sistema
"""

import asyncio
import platform
import logging
from typing import Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SystemInfo:
    """
    Obtém informações do sistema
    
    - CPU, RAM, Disco
    - Bateria (se disponível)
    - Uptime
    - Info do SO
    """
    
    def __init__(self):
        self._psutil = None
        self._boot_time = None
        
        self._initialize()
    
    def _initialize(self):
        """Inicializa psutil"""
        try:
            import psutil
            self._psutil = psutil
            self._boot_time = datetime.fromtimestamp(psutil.boot_time())
        except ImportError:
            logger.warning("psutil não instalado: pip install psutil")
    
    async def get_all(self) -> Dict:
        """Retorna todas as informações do sistema"""
        if not self._psutil:
            return {
                'cpu_percent': 'N/A',
                'memory_percent': 'N/A',
                'memory_used': 'N/A',
                'disk_percent': 'N/A',
                'disk_used': 'N/A',
                'battery': 'N/A',
                'uptime': 'N/A'
            }
        
        loop = asyncio.get_event_loop()
        
        def _get_info():
            # CPU
            cpu_percent = self._psutil.cpu_percent(interval=1)
            
            # RAM
            memory = self._psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = self._format_bytes(memory.used)
            memory_total = self._format_bytes(memory.total)
            
            # Disco
            disk = self._psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used = self._format_bytes(disk.used)
            disk_total = self._format_bytes(disk.total)
            
            # Bateria
            battery = self._psutil.sensors_battery()
            if battery:
                battery_str = f"{battery.percent}%"
                if battery.power_plugged:
                    battery_str += " (carregando)"
            else:
                battery_str = "N/A"
            
            # Uptime
            uptime = datetime.now() - self._boot_time
            uptime_str = self._format_timedelta(uptime)
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_used': f"{memory_used}/{memory_total}",
                'disk_percent': disk_percent,
                'disk_used': f"{disk_used}/{disk_total}",
                'battery': battery_str,
                'uptime': uptime_str
            }
        
        return await loop.run_in_executor(None, _get_info)
    
    async def get_cpu(self) -> Dict:
        """Informações da CPU"""
        if not self._psutil:
            return {}
        
        loop = asyncio.get_event_loop()
        
        def _get():
            return {
                'percent': self._psutil.cpu_percent(interval=1),
                'count': self._psutil.cpu_count(),
                'count_logical': self._psutil.cpu_count(logical=True),
                'freq': self._psutil.cpu_freq().current if self._psutil.cpu_freq() else 0
            }
        
        return await loop.run_in_executor(None, _get)
    
    async def get_memory(self) -> Dict:
        """Informações da memória"""
        if not self._psutil:
            return {}
        
        mem = self._psutil.virtual_memory()
        
        return {
            'total': self._format_bytes(mem.total),
            'available': self._format_bytes(mem.available),
            'used': self._format_bytes(mem.used),
            'percent': mem.percent
        }
    
    async def get_disk(self, path: str = '/') -> Dict:
        """Informações do disco"""
        if not self._psutil:
            return {}
        
        disk = self._psutil.disk_usage(path)
        
        return {
            'total': self._format_bytes(disk.total),
            'used': self._format_bytes(disk.used),
            'free': self._format_bytes(disk.free),
            'percent': disk.percent
        }
    
    async def get_processes(self, limit: int = 10) -> list:
        """Lista processos por uso de CPU"""
        if not self._psutil:
            return []
        
        loop = asyncio.get_event_loop()
        
        def _get():
            procs = []
            for proc in self._psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    procs.append(proc.info)
                except:
                    pass
            
            # Ordena por CPU
            procs.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            return procs[:limit]
        
        return await loop.run_in_executor(None, _get)
    
    def get_os_info(self) -> Dict:
        """Informações do SO"""
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python': platform.python_version()
        }
    
    def _format_bytes(self, bytes: int) -> str:
        """Formata bytes para humano"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024:
                return f"{bytes:.1f}{unit}"
            bytes /= 1024
        return f"{bytes:.1f}PB"
    
    def _format_timedelta(self, td: timedelta) -> str:
        """Formata timedelta para humano"""
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        
        return ' '.join(parts) or "< 1m"
