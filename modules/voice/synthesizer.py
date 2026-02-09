# -*- coding: utf-8 -*-
"""
Synthesizer - Text-to-Speech
"""

import asyncio
import logging
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class Synthesizer:
    """
    Sintetiza texto em fala
    
    Suporta:
    - pyttsx3 (offline, gratuito)
    - ElevenLabs (online, alta qualidade)
    - Azure TTS (online)
    """
    
    def __init__(self, speed: int = 180, language: str = "pt-BR"):
        self.speed = speed
        self.language = language
        self.volume = 1.0
        
        self._engine = None
        self._use_elevenlabs = False
        self._elevenlabs_client = None
        self._initialized = False
        
        # Diretório para sons
        self._sounds_dir = Path(__file__).parent / 'sounds'
    
    async def initialize(self):
        """Inicializa o sintetizador"""
        # Tenta ElevenLabs primeiro (melhor qualidade)
        try:
            await self._init_elevenlabs()
            return
        except Exception as e:
            logger.debug(f"ElevenLabs não disponível: {e}")
        
        # Fallback para pyttsx3 (offline)
        try:
            await self._init_pyttsx3()
            return
        except Exception as e:
            logger.debug(f"pyttsx3 não disponível: {e}")
        
        logger.warning("Nenhum backend de TTS disponível")
    
    async def _init_elevenlabs(self):
        """Inicializa ElevenLabs"""
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key or api_key == 'sua_chave_aqui':
            raise ValueError("ELEVENLABS_API_KEY não configurada")
        
        try:
            from elevenlabs import ElevenLabs
            
            self._elevenlabs_client = ElevenLabs(api_key=api_key)
            self._voice_id = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')
            self._use_elevenlabs = True
            self._initialized = True
            logger.info("ElevenLabs TTS inicializado")
            
        except ImportError:
            raise ImportError("Instale elevenlabs: pip install elevenlabs")
    
    async def _init_pyttsx3(self):
        """Inicializa pyttsx3"""
        try:
            import pyttsx3
            
            loop = asyncio.get_event_loop()
            self._engine = await loop.run_in_executor(
                None,
                pyttsx3.init
            )
            
            # Configura voz
            self._engine.setProperty('rate', self.speed)
            self._engine.setProperty('volume', self.volume)
            
            # Tenta selecionar voz em português
            voices = self._engine.getProperty('voices')
            for voice in voices:
                if 'brazil' in voice.name.lower() or 'portuguese' in voice.name.lower():
                    self._engine.setProperty('voice', voice.id)
                    break
            
            self._use_elevenlabs = False
            self._initialized = True
            logger.info("pyttsx3 TTS inicializado")
            
        except ImportError:
            raise ImportError("Instale pyttsx3: pip install pyttsx3")
        except Exception as e:
            raise RuntimeError(f"Erro inicializando pyttsx3: {e}")
    
    async def speak(self, text: str):
        """
        Fala o texto
        
        Args:
            text: Texto para sintetizar e falar
        """
        if not self._initialized:
            logger.warning("Synthesizer não inicializado")
            return
        
        try:
            if self._use_elevenlabs:
                await self._speak_elevenlabs(text)
            else:
                await self._speak_pyttsx3(text)
                
        except Exception as e:
            logger.error(f"Erro ao falar: {e}")
    
    async def _speak_elevenlabs(self, text: str):
        """Fala usando ElevenLabs"""
        try:
            from elevenlabs import play
            
            loop = asyncio.get_event_loop()
            
            # Gera áudio
            audio = await loop.run_in_executor(
                None,
                lambda: self._elevenlabs_client.generate(
                    text=text,
                    voice=self._voice_id,
                    model="eleven_multilingual_v2"
                )
            )
            
            # Toca áudio
            await loop.run_in_executor(None, lambda: play(audio))
            
        except Exception as e:
            logger.error(f"Erro ElevenLabs: {e}")
            # Fallback para pyttsx3
            await self._init_pyttsx3()
            await self._speak_pyttsx3(text)
    
    async def _speak_pyttsx3(self, text: str):
        """Fala usando pyttsx3"""
        if not self._engine:
            return
        
        loop = asyncio.get_event_loop()
        
        def _speak():
            self._engine.say(text)
            self._engine.runAndWait()
        
        await loop.run_in_executor(None, _speak)
    
    async def play_sound(self, sound_name: str):
        """
        Toca um som de efeito
        
        Args:
            sound_name: Nome do som (listening, success, error)
        """
        sound_file = self._sounds_dir / f"{sound_name}.wav"
        
        if not sound_file.exists():
            logger.debug(f"Som não encontrado: {sound_file}")
            return
        
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(str(sound_file))
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
        except ImportError:
            logger.debug("pygame não disponível para sons")
        except Exception as e:
            logger.debug(f"Erro tocando som: {e}")
    
    def set_volume(self, volume: float):
        """Define volume (0.0 a 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        
        if self._engine:
            self._engine.setProperty('volume', self.volume)
    
    def set_speed(self, speed: int):
        """Define velocidade da fala"""
        self.speed = speed
        
        if self._engine:
            self._engine.setProperty('rate', self.speed)
    
    def is_available(self) -> bool:
        """Verifica se síntese está disponível"""
        return self._initialized
