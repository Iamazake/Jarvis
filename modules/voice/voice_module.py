# -*- coding: utf-8 -*-
"""
Voice Module - Módulo Principal de Voz
Integra STT, TTS e Wake Word

Autor: JARVIS Team
Versão: 3.0.0
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)


class VoiceModule:
    """
    Módulo de voz completo
    
    Funcionalidades:
    - Wake word detection ("Hey Jarvis")
    - Speech-to-Text (Whisper)
    - Text-to-Speech (pyttsx3/ElevenLabs)
    - Modo contínuo de escuta
    """
    
    def __init__(self, config):
        self.config = config
        self._running = False
        self._listening = False
        
        # Componentes
        self.listener: Optional['AudioListener'] = None
        self.transcriber: Optional['Transcriber'] = None
        self.synthesizer: Optional['Synthesizer'] = None
        
        # Callbacks
        self._on_wake_word: Optional[Callable] = None
        self._on_speech: Optional[Callable] = None
        
        # Configurações
        self.wake_word = config.get('JARVIS_WAKE_WORD', 'jarvis')
        self.language = config.get('JARVIS_LANGUAGE', 'pt-BR')
        self.voice_speed = config.get('JARVIS_VOICE_SPEED', 180)
        
        self.status = '🔴'
    
    async def start(self):
        """Inicializa componentes de voz"""
        logger.info("🎤 Iniciando módulo de voz...")
        
        try:
            # Inicializa TTS (Text-to-Speech)
            from .synthesizer import Synthesizer
            self.synthesizer = Synthesizer(
                speed=self.voice_speed,
                language=self.language
            )
            await self.synthesizer.initialize()
            logger.info("  ✅ TTS inicializado")
            
        except Exception as e:
            logger.warning(f"  ⚠️ TTS: {e}")
        
        try:
            # Inicializa STT (Speech-to-Text)
            from .transcriber import Transcriber
            self.transcriber = Transcriber(
                model=self.config.get('WHISPER_MODEL', 'base'),
                language=self.language[:2]  # 'pt'
            )
            await self.transcriber.initialize()
            logger.info("  ✅ STT inicializado")
            
        except Exception as e:
            logger.warning(f"  ⚠️ STT: {e}")
        
        try:
            # Inicializa Listener (captura de áudio)
            from .listener import AudioListener
            self.listener = AudioListener(
                wake_word=self.wake_word
            )
            logger.info("  ✅ Listener inicializado")
            
        except Exception as e:
            logger.warning(f"  ⚠️ Listener: {e}")
        
        self._running = True
        self.status = '🟢'
        logger.info("✅ Módulo de voz pronto")
    
    async def stop(self):
        """Para o módulo de voz"""
        self._running = False
        self._listening = False
        
        if self.listener:
            self.listener.stop()
        
        self.status = '🔴'
        logger.info("⏹️ Módulo de voz parado")
    
    async def speak(self, text: str, wait: bool = True) -> bool:
        """
        Fala um texto
        
        Args:
            text: Texto para falar
            wait: Aguardar conclusão
        
        Returns:
            True se falou com sucesso
        """
        if not self.synthesizer:
            logger.warning("TTS não disponível")
            return False
        
        try:
            if wait:
                await self.synthesizer.speak(text)
            else:
                asyncio.create_task(self.synthesizer.speak(text))
            return True
            
        except Exception as e:
            logger.error(f"Erro ao falar: {e}")
            return False
    
    async def listen(self, timeout: float = 10.0) -> Optional[str]:
        """
        Escuta e transcreve áudio
        
        Args:
            timeout: Tempo máximo de escuta
        
        Returns:
            Texto transcrito ou None
        """
        if not self.listener or not self.transcriber:
            logger.warning("Listener ou Transcriber não disponível")
            return None
        
        try:
            # Captura áudio
            audio_data = await self.listener.listen(timeout=timeout)
            
            if not audio_data:
                return None
            
            # Transcreve
            text = await self.transcriber.transcribe(audio_data)
            
            return text
            
        except Exception as e:
            logger.error(f"Erro ao escutar: {e}")
            return None
    
    async def listen_for_wake_word(self, callback: Callable):
        """
        Escuta continuamente por wake word
        
        Args:
            callback: Função chamada quando detectar wake word
        """
        if not self.listener:
            logger.warning("Listener não disponível")
            return
        
        self._on_wake_word = callback
        self._listening = True
        
        logger.info(f"👂 Escutando por '{self.wake_word}'...")
        
        while self._listening and self._running:
            try:
                detected = await self.listener.detect_wake_word()
                
                if detected:
                    logger.info("🎯 Wake word detectado!")
                    
                    # Toca som de confirmação
                    if self.synthesizer:
                        await self.synthesizer.play_sound('listening')
                    
                    if self._on_wake_word:
                        await self._on_wake_word()
                
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no wake word: {e}")
                await asyncio.sleep(1)
    
    def stop_listening(self):
        """Para de escutar por wake word"""
        self._listening = False
    
    async def process(self, message: str, intent, context: Dict, metadata: Dict) -> str:
        """
        Processa comando de voz (chamado pelo orchestrator)
        
        Usado para comandos como "fale mais alto", "repita", etc
        """
        intent_type = intent.type if hasattr(intent, 'type') else str(intent)
        
        if intent_type == 'voice_volume_up':
            if self.synthesizer:
                self.synthesizer.set_volume(min(1.0, self.synthesizer.volume + 0.2))
            return "Volume aumentado, senhor."
        
        elif intent_type == 'voice_volume_down':
            if self.synthesizer:
                self.synthesizer.set_volume(max(0.1, self.synthesizer.volume - 0.2))
            return "Volume diminuído."
        
        elif intent_type == 'voice_repeat':
            last_response = context.get('last_response')
            if last_response:
                return last_response
            return "Não tenho nada para repetir."
        
        return "Comando de voz não reconhecido."
    
    def is_available(self) -> bool:
        """Verifica se módulo está disponível"""
        return self._running and (self.synthesizer is not None or self.transcriber is not None)
