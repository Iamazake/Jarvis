# -*- coding: utf-8 -*-
"""
Semantic Cache - Cache com Embeddings FAISS
Singleton Pattern + Repository Pattern

Autor: JARVIS Team
Versão: 4.0.0
"""

import os
import re
import hashlib
import logging
import pickle
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Imports opcionais
try:
    import faiss
    import numpy as np
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    logger.warning("⚠️ FAISS não instalado: pip install faiss-cpu")

try:
    from sentence_transformers import SentenceTransformer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    logger.warning("⚠️ sentence-transformers não instalado")


# Configurações
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
INDEX_FILE = CACHE_DIR / "faiss.index"
META_FILE = CACHE_DIR / "metadata.pkl"

SIMILARITY_THRESHOLD = 0.92
DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


class SemanticCache:
    """
    Cache Semântico com FAISS
    
    Singleton Pattern: Garante única instância do índice
    
    Uso:
        cache = SemanticCache()
        cache.set("pergunta", "resposta")
        resposta = cache.get("pergunta similar")
    """
    
    _instance: Optional['SemanticCache'] = None
    _model: Optional['SentenceTransformer'] = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, model_name: str = None):
        """
        Inicializa o cache
        
        Args:
            model_name: Nome do modelo de embeddings
        """
        if self._initialized:
            return
        
        self.model_name = model_name or DEFAULT_MODEL
        self.index: Optional['faiss.IndexFlatIP'] = None
        self.metadata: List[Dict] = []
        
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        self._load_model()
        self._load_index()
        
        self._initialized = True
        logger.info("✅ Cache semântico inicializado")
    
    def get(self, question: str, threshold: float = None) -> Optional[str]:
        """
        Busca resposta no cache
        
        Args:
            question: Pergunta a buscar
            threshold: Similaridade mínima (0-1)
            
        Returns:
            Resposta cacheada ou None
        """
        if not self._is_ready():
            return None
        
        threshold = threshold or SIMILARITY_THRESHOLD
        
        # Limpar pergunta
        clean_q = self._clean_text(question)
        q_hash = self._hash(clean_q)
        
        # 1. Busca exata por hash
        for entry in self.metadata:
            if entry.get("hash") == q_hash:
                if not self._is_expired(entry):
                    logger.info("📦 Cache HIT (hash exato)")
                    return entry.get("answer")
        
        # 2. Busca semântica
        if self.index is None or self.index.ntotal == 0:
            return None
        
        try:
            # Gerar embedding
            vec = self._model.encode([clean_q], normalize_embeddings=True)
            vec = vec.astype('float32')
            
            # Buscar
            D, I = self.index.search(vec, 1)
            similarity = D[0][0]
            idx = I[0][0]
            
            if similarity >= threshold and idx < len(self.metadata):
                entry = self.metadata[idx]
                if not self._is_expired(entry):
                    logger.info(f"📦 Cache HIT (semântico, sim={similarity:.3f})")
                    return entry.get("answer")
                    
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
        
        return None
    
    def set(self, question: str, answer: str, ttl_hours: int = 24):
        """
        Salva resposta no cache
        
        Args:
            question: Pergunta original
            answer: Resposta a cachear
            ttl_hours: Tempo de vida em horas
        """
        if not self._is_ready():
            return
        
        clean_q = self._clean_text(question)
        q_hash = self._hash(clean_q)
        
        # Verificar se já existe
        for i, entry in enumerate(self.metadata):
            if entry.get("hash") == q_hash:
                # Atualizar existente
                self.metadata[i]["answer"] = answer
                self.metadata[i]["updated_at"] = datetime.now().isoformat()
                self._save_index()
                return
        
        try:
            # Gerar embedding
            vec = self._model.encode([clean_q], normalize_embeddings=True)
            vec = vec.astype('float32')
            
            # Adicionar ao índice
            if self.index is None:
                self.index = faiss.IndexFlatIP(vec.shape[1])
            
            self.index.add(vec)
            
            # Adicionar metadata
            self.metadata.append({
                "hash": q_hash,
                "question": question[:200],
                "answer": answer,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
            })
            
            self._save_index()
            logger.debug(f"📝 Cache salvo: {question[:50]}...")
            
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {e}")
    
    def clear(self):
        """Limpa todo o cache"""
        self.index = None
        self.metadata = []
        
        if INDEX_FILE.exists():
            INDEX_FILE.unlink()
        if META_FILE.exists():
            META_FILE.unlink()
        
        logger.info("🗑️ Cache limpo")
    
    def stats(self) -> Dict:
        """Retorna estatísticas do cache"""
        total = len(self.metadata)
        expired = sum(1 for e in self.metadata if self._is_expired(e))
        
        return {
            "total_entries": total,
            "active_entries": total - expired,
            "expired_entries": expired,
            "index_size": self.index.ntotal if self.index else 0,
            "model": self.model_name
        }
    
    # ========== Métodos Privados ==========
    
    def _is_ready(self) -> bool:
        """Verifica se o cache está pronto"""
        return HAS_FAISS and HAS_TRANSFORMERS and self._model is not None
    
    def _load_model(self):
        """Carrega modelo de embeddings"""
        if not HAS_TRANSFORMERS:
            return
        
        if SemanticCache._model is None:
            try:
                logger.info(f"📦 Carregando modelo: {self.model_name}")
                SemanticCache._model = SentenceTransformer(self.model_name)
                logger.info("✅ Modelo carregado")
            except Exception as e:
                logger.error(f"❌ Erro ao carregar modelo: {e}")
        
        self._model = SemanticCache._model
    
    def _load_index(self):
        """Carrega índice do disco"""
        if not HAS_FAISS:
            return
        
        try:
            if INDEX_FILE.exists():
                self.index = faiss.read_index(str(INDEX_FILE))
                logger.info(f"📂 Índice carregado: {self.index.ntotal} vetores")
            
            if META_FILE.exists():
                with open(META_FILE, 'rb') as f:
                    self.metadata = pickle.load(f)
                    
        except Exception as e:
            logger.warning(f"⚠️ Erro ao carregar cache: {e}")
            self.index = None
            self.metadata = []
    
    def _save_index(self):
        """Salva índice no disco"""
        if not HAS_FAISS or self.index is None:
            return
        
        try:
            faiss.write_index(self.index, str(INDEX_FILE))
            
            with open(META_FILE, 'wb') as f:
                pickle.dump(self.metadata, f)
                
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {e}")
    
    def _clean_text(self, text: str) -> str:
        """Limpa texto para busca"""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _hash(self, text: str) -> str:
        """Gera hash do texto"""
        return hashlib.sha256(text.encode()).hexdigest()[:32]
    
    def _is_expired(self, entry: Dict) -> bool:
        """Verifica se entrada expirou"""
        expires = entry.get("expires_at")
        if not expires:
            return False
        
        try:
            expires_dt = datetime.fromisoformat(expires)
            return datetime.now() > expires_dt
        except:
            return False


# Funções de conveniência (compatibilidade com código antigo)
_cache_instance: Optional[SemanticCache] = None


def get_cached_answer(question: str, threshold: float = SIMILARITY_THRESHOLD) -> Optional[str]:
    """Busca resposta no cache"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticCache()
    return _cache_instance.get(question, threshold)


def cache_answer(question: str, answer: str, ttl_hours: int = 24):
    """Salva resposta no cache"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticCache()
    _cache_instance.set(question, answer, ttl_hours)


def get_cache_stats() -> Dict:
    """Retorna estatísticas do cache"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticCache()
    return _cache_instance.stats()
