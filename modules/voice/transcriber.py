# -*- coding: utf-8 -*-
"""
Transcriber - Speech-to-Text usando Whisper
"""

import asyncio
import logging
import tempfile
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class Transcriber:
    """
    Transcreve áudio para texto usando Whisper
    
    Suporta:
    - OpenAI Whisper local (whisper)
    - OpenAI Whisper API
    - Faster Whisper (mais rápido)
    """
    
    def __init__(self, model: str = "base", language: str = "pt"):
        self.model_name = model
        self.language = language
        self._model = None
        self._use_api = False
        self._initialized = False
    
    async def initialize(self):
        """Inicializa o modelo Whisper"""
        # Tenta carregar Whisper local
        try:
            await self._init_local_whisper()
            return
        except Exception as e:
            logger.debug(f"Whisper local não disponível: {e}")
        
        # Tenta usar API do OpenAI
        try:
            await self._init_whisper_api()
            return
        except Exception as e:
            logger.debug(f"Whisper API não disponível: {e}")
        
        logger.warning("Nenhum backend de STT disponível")
    
    async def _init_local_whisper(self):
        """Inicializa Whisper local"""
        # Tenta faster-whisper primeiro (mais rápido)
        try:
            from faster_whisper import WhisperModel
            
            # Roda em thread separada para não bloquear
            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(
                None,
                lambda: WhisperModel(self.model_name, device="cpu", compute_type="int8")
            )
            self._use_api = False
            self._initialized = True
            logger.info(f"Faster Whisper '{self.model_name}' carregado")
            return
            
        except ImportError:
            pass
        
        # Fallback para whisper padrão
        try:
            import whisper
            
            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(
                None,
                lambda: whisper.load_model(self.model_name)
            )
            self._use_api = False
            self._initialized = True
            logger.info(f"Whisper '{self.model_name}' carregado")
            return
            
        except ImportError:
            raise ImportError("Instale whisper ou faster-whisper")
    
    async def _init_whisper_api(self):
        """Inicializa cliente da API Whisper"""
        try:
            from openai import OpenAI
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY não configurada")
            
            self._client = OpenAI(api_key=api_key)
            self._use_api = True
            self._initialized = True
            logger.info("Whisper API inicializado")
            
        except ImportError:
            raise ImportError("Instale openai: pip install openai")
    
    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        Transcreve áudio para texto
        
        Args:
            audio_data: Dados de áudio em bytes (16kHz, mono, int16)
        
        Returns:
            Texto transcrito ou None
        """
        if not self._initialized:
            logger.warning("Transcriber não inicializado")
            return None
        
        try:
            if self._use_api:
                return await self._transcribe_api(audio_data)
            else:
                return await self._transcribe_local(audio_data)
                
        except Exception as e:
            logger.error(f"Erro na transcrição: {e}")
            return None
    
    async def _transcribe_local(self, audio_data: bytes) -> Optional[str]:
        """Transcreve usando modelo local"""
        # Salva áudio temporário
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_path = f.name
            
            # Escreve header WAV
            import struct
            sample_rate = 16000
            num_samples = len(audio_data) // 2
            
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + len(audio_data)))
            f.write(b'WAVE')
            f.write(b'fmt ')
            f.write(struct.pack('<I', 16))  # Subchunk1Size
            f.write(struct.pack('<H', 1))   # AudioFormat (PCM)
            f.write(struct.pack('<H', 1))   # NumChannels
            f.write(struct.pack('<I', sample_rate))  # SampleRate
            f.write(struct.pack('<I', sample_rate * 2))  # ByteRate
            f.write(struct.pack('<H', 2))   # BlockAlign
            f.write(struct.pack('<H', 16))  # BitsPerSample
            f.write(b'data')
            f.write(struct.pack('<I', len(audio_data)))
            f.write(audio_data)
        
        try:
            loop = asyncio.get_event_loop()
            
            # Verifica se é faster-whisper ou whisper padrão
            if hasattr(self._model, 'transcribe'):
                # Whisper padrão
                result = await loop.run_in_executor(
                    None,
                    lambda: self._model.transcribe(
                        temp_path,
                        language=self.language,
                        fp16=False
                    )
                )
                return result.get('text', '').strip()
            else:
                # Faster-whisper
                segments, _ = await loop.run_in_executor(
                    None,
                    lambda: self._model.transcribe(
                        temp_path,
                        language=self.language
                    )
                )
                text = ' '.join([seg.text for seg in segments])
                return text.strip()
                
        finally:
            # Remove arquivo temporário
            try:
                os.unlink(temp_path)
            except:
                pass
    
    async def _transcribe_api(self, audio_data: bytes) -> Optional[str]:
        """Transcreve usando API do OpenAI"""
        # Salva áudio temporário
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_path = f.name
            
            # Escreve header WAV
            import struct
            sample_rate = 16000
            
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + len(audio_data)))
            f.write(b'WAVE')
            f.write(b'fmt ')
            f.write(struct.pack('<I', 16))
            f.write(struct.pack('<H', 1))
            f.write(struct.pack('<H', 1))
            f.write(struct.pack('<I', sample_rate))
            f.write(struct.pack('<I', sample_rate * 2))
            f.write(struct.pack('<H', 2))
            f.write(struct.pack('<H', 16))
            f.write(b'data')
            f.write(struct.pack('<I', len(audio_data)))
            f.write(audio_data)
        
        try:
            loop = asyncio.get_event_loop()
            
            with open(temp_path, 'rb') as audio_file:
                result = await loop.run_in_executor(
                    None,
                    lambda: self._client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language=self.language
                    )
                )
            
            return result.text.strip()
            
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def is_available(self) -> bool:
        """Verifica se transcrição está disponível"""
        return self._initialized
