"""
Media Monitor - Salva e notifica mídias de contatos específicos
"""

import os
import base64
import hashlib
import requests
from pathlib import Path
from typing import Set, Dict, Optional
from datetime import datetime
from .base import AbstractMonitor, logger


class MediaMonitor(AbstractMonitor):
    """
    Monitora e salva mídias (fotos, vídeos, áudios, documentos)
    enviadas por contatos específicos.
    """
    
    MEDIA_TYPES = {'image', 'video', 'audio', 'document', 'sticker'}
    
    def __init__(self, notifier_jid: str, contacts: Set[str] = None,
                 save_path: str = "data/media", 
                 notify_on_media: bool = True,
                 save_media: bool = True):
        """
        Args:
            notifier_jid: JID que recebe alertas
            contacts: Set de JIDs a monitorar (None = todos)
            save_path: Diretório para salvar mídias
            notify_on_media: Enviar notificação quando receber mídia
            save_media: Se True, salva o arquivo localmente
        """
        super().__init__(notifier_jid, "MediaMonitor")
        self.contacts: Optional[Set[str]] = contacts  # None = monitora todos
        self.save_path = Path(save_path)
        self.notify_on_media = notify_on_media
        self.save_media = save_media
        
        # Cria diretório se não existir
        self.save_path.mkdir(parents=True, exist_ok=True)
        
        # Histórico de mídias recebidas
        self._media_history: list = []
    
    def add_contact(self, jid: str):
        """Adiciona contato ao monitoramento de mídia"""
        if self.contacts is None:
            self.contacts = set()
        if '@' not in jid:
            jid = f"{jid}@s.whatsapp.net"
        self.contacts.add(jid)
    
    def remove_contact(self, jid: str):
        """Remove contato do monitoramento"""
        if self.contacts:
            if '@' not in jid:
                jid = f"{jid}@s.whatsapp.net"
            self.contacts.discard(jid)
    
    def monitor_all(self):
        """Configura para monitorar mídias de todos os contatos"""
        self.contacts = None
    
    def _should_monitor(self, sender: str) -> bool:
        """Verifica se deve monitorar este sender"""
        if self.contacts is None:
            return True  # Monitora todos
        return sender in self.contacts
    
    def _get_extension(self, media_type: str, mimetype: str = None) -> str:
        """Determina extensão do arquivo"""
        ext_map = {
            'image': '.jpg',
            'video': '.mp4',
            'audio': '.ogg',
            'document': '.pdf',
            'sticker': '.webp'
        }
        
        if mimetype:
            # Extrai extensão do mimetype (image/jpeg -> jpeg)
            parts = mimetype.split('/')
            if len(parts) == 2:
                ext = parts[1].split(';')[0]  # Remove parâmetros
                return f".{ext}"
        
        return ext_map.get(media_type, '.bin')
    
    def _save_media(self, media_data: bytes, sender: str, 
                    media_type: str, mimetype: str = None) -> Optional[Path]:
        """Salva mídia no disco"""
        try:
            # Cria subdiretório por contato
            contact_dir = self.save_path / sender.split('@')[0]
            contact_dir.mkdir(exist_ok=True)
            
            # Nome do arquivo: timestamp_hash.ext
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_hash = hashlib.md5(media_data[:1024]).hexdigest()[:8]
            ext = self._get_extension(media_type, mimetype)
            filename = f"{timestamp}_{file_hash}{ext}"
            
            filepath = contact_dir / filename
            filepath.write_bytes(media_data)
            
            logger.info(f"[MediaMonitor] Mídia salva: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"[MediaMonitor] Erro ao salvar mídia: {e}")
            return None
    
    async def _download_media(self, url: str) -> Optional[bytes]:
        """Baixa mídia de URL (se fornecida pelo Baileys)"""
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            logger.error(f"[MediaMonitor] Erro ao baixar mídia: {e}")
        return None
    
    def update(self, event: dict) -> None:
        """
        Processa eventos de mídia.
        """
        if not self.enabled or event.get('type') != 'media':
            return
        
        sender = event.get('sender', '')
        if not self._should_monitor(sender):
            return
        
        data = event.get('data', {})
        media_type = data.get('mediaType', 'unknown')
        mimetype = data.get('mimetype', '')
        caption = data.get('caption', '')
        push_name = event.get('push_name', sender.split('@')[0])
        
        # Salva mídia se configurado e dados disponíveis
        saved_path = None
        if self.save_media:
            media_base64 = data.get('base64')
            if media_base64:
                try:
                    media_bytes = base64.b64decode(media_base64)
                    saved_path = self._save_media(media_bytes, sender, media_type, mimetype)
                except Exception as e:
                    logger.error(f"[MediaMonitor] Erro ao decodificar base64: {e}")
        
        # Registra no histórico
        record = {
            'sender': sender,
            'push_name': push_name,
            'media_type': media_type,
            'mimetype': mimetype,
            'caption': caption,
            'saved_path': str(saved_path) if saved_path else None,
            'timestamp': datetime.now().isoformat()
        }
        self._media_history.append(record)
        
        # Limita histórico a 1000 registros
        if len(self._media_history) > 1000:
            self._media_history = self._media_history[-500:]
        
        # Notifica
        if self.notify_on_media:
            type_emoji = {
                'image': '🖼️',
                'video': '🎬',
                'audio': '🎵',
                'document': '📄',
                'sticker': '🎨'
            }
            emoji = type_emoji.get(media_type, '📎')
            
            alert = (
                f"{emoji} Mídia recebida!\n"
                f"👤 De: {push_name}\n"
                f"📦 Tipo: {media_type}"
            )
            if caption:
                alert += f"\n📝 Legenda: {caption[:50]}..."
            if saved_path:
                alert += f"\n💾 Salvo em: {saved_path.name}"
            
            self.notify(alert)
    
    def get_media_history(self, limit: int = 50) -> list:
        """Retorna histórico de mídias recebidas"""
        return self._media_history[-limit:]
    
    def __repr__(self):
        contacts_str = "todos" if self.contacts is None else str(len(self.contacts))
        return f"<MediaMonitor contacts={contacts_str} enabled={self.enabled}>"
