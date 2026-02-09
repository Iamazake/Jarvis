# -*- coding: utf-8 -*-
"""
Audio Listener - Captura de Áudio e Wake Word Detection
"""

import asyncio
import logging
import queue
import threading
from typing import Optional, Callable
import numpy as np

logger = logging.getLogger(__name__)

# Constantes de áudio
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
CHANNELS = 1


class AudioListener:
    """
    Captura áudio do microfone
    
    Funcionalidades:
    - Captura contínua de áudio
    - Detecção de wake word (pvporcupine ou simples)
    - Voice Activity Detection (VAD)
    """
    
    def __init__(self, wake_word: str = "jarvis"):
        self.wake_word = wake_word.lower()
        self._running = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._stream = None
        self._pyaudio = None
        
        # Wake word detector (pvporcupine se disponível)
        self._porcupine = None
        self._use_porcupine = False
        
        self._initialize_audio()
    
    def _initialize_audio(self):
        """Inicializa PyAudio"""
        try:
            import pyaudio
            self._pyaudio = pyaudio.PyAudio()
            logger.debug("PyAudio inicializado")
            
            # Tenta inicializar Porcupine para wake word
            self._try_init_porcupine()
            
        except ImportError:
            logger.warning("PyAudio não instalado. Use: pip install pyaudio")
        except Exception as e:
            logger.error(f"Erro inicializando áudio: {e}")
    
    def _try_init_porcupine(self):
        """Tenta inicializar Porcupine para wake word detection"""
        try:
            import pvporcupine
            
            # Porcupine requer uma access key
            # Por enquanto, usamos detecção simples
            logger.debug("Porcupine disponível, mas usando detecção simples")
            
        except ImportError:
            logger.debug("Porcupine não disponível, usando detecção simples")
    
    async def listen(self, timeout: float = 10.0) -> Optional[bytes]:
        """
        Escuta áudio por um período
        
        Args:
            timeout: Tempo máximo de escuta em segundos
        
        Returns:
            Dados de áudio em bytes ou None
        """
        if not self._pyaudio:
            return None
        
        import pyaudio
        
        try:
            # Abre stream
            stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            
            logger.debug(f"Escutando por {timeout}s...")
            
            frames = []
            silence_count = 0
            max_silence = int(SAMPLE_RATE / CHUNK_SIZE * 2)  # 2 segundos de silêncio
            
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Verifica timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    break
                
                # Lê chunk de áudio
                try:
                    data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    frames.append(data)
                    
                    # Detecta silêncio (VAD simples)
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    volume = np.abs(audio_data).mean()
                    
                    if volume < 500:  # Threshold de silêncio
                        silence_count += 1
                        if silence_count > max_silence and len(frames) > 10:
                            # Silêncio prolongado após fala = fim
                            break
                    else:
                        silence_count = 0
                        
                except Exception as e:
                    logger.debug(f"Erro lendo áudio: {e}")
                    break
                
                # Yield para não bloquear
                await asyncio.sleep(0.01)
            
            stream.stop_stream()
            stream.close()
            
            if frames:
                return b''.join(frames)
            
            return None
            
        except Exception as e:
            logger.error(f"Erro capturando áudio: {e}")
            return None
    
    async def detect_wake_word(self) -> bool:
        """
        Detecta wake word no áudio
        
        Returns:
            True se wake word detectado
        """
        if not self._pyaudio:
            return False
        
        import pyaudio
        
        try:
            # Captura pequeno chunk de áudio
            stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE * 4
            )
            
            data = stream.read(CHUNK_SIZE * 4, exception_on_overflow=False)
            
            stream.stop_stream()
            stream.close()
            
            # Detecta se há áudio significativo
            audio_data = np.frombuffer(data, dtype=np.int16)
            volume = np.abs(audio_data).mean()
            
            # Se volume baixo, não há wake word
            if volume < 1000:
                return False
            
            # TODO: Implementar detecção real de wake word
            # Por ora, retorna False (precisa de modelo treinado)
            
            return False
            
        except Exception as e:
            logger.debug(f"Erro detectando wake word: {e}")
            return False
    
    def stop(self):
        """Para o listener"""
        self._running = False
        
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except:
                pass
        
        if self._porcupine:
            try:
                self._porcupine.delete()
            except:
                pass
    
    def __del__(self):
        self.stop()
        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except:
                pass
