# -*- coding: utf-8 -*-
"""
Métricas Prometheus para observabilidade
Contadores, histogramas e gauges para mensagens, latência e monitores.

Para expor: se usar FastAPI, adicione no app:
  from prometheus_client import make_asgi_app
  metrics_app = make_asgi_app()
  app.mount("/metrics", metrics_app)
"""

import logging
import time
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

_metrics_available = False
messages_sent = None
message_latency = None
active_monitors = None


def _init_metrics() -> None:
    global _metrics_available, messages_sent, message_latency, active_monitors
    if _metrics_available:
        return
    try:
        from prometheus_client import Counter, Gauge, Histogram
        messages_sent = Counter(
            "jarvis_messages_sent_total",
            "Total de mensagens enviadas (ex.: WhatsApp)",
        )
        message_latency = Histogram(
            "jarvis_message_latency_seconds",
            "Tempo de processamento de mensagem em segundos",
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )
        active_monitors = Gauge(
            "jarvis_active_monitors",
            "Número de contatos em monitoramento ativo",
        )
        _metrics_available = True
    except ImportError:
        logger.debug("prometheus_client não instalado; métricas desativadas")


def inc_messages_sent() -> None:
    """Incrementa contador de mensagens enviadas."""
    _init_metrics()
    if messages_sent is not None:
        messages_sent.inc()


def observe_message_latency(seconds: float) -> None:
    """Registra latência de processamento de uma mensagem."""
    _init_metrics()
    if message_latency is not None:
        message_latency.observe(seconds)


def set_active_monitors(value: int) -> None:
    """Define o número de monitores ativos (contatos monitorados)."""
    _init_metrics()
    if active_monitors is not None:
        active_monitors.set(value)


@contextmanager
def time_message_processing():
    """
    Context manager para medir tempo de processamento.
    Uso: with time_message_processing(): ... process ...
    """
    _init_metrics()
    start = time.perf_counter()
    try:
        yield
    finally:
        if message_latency is not None:
            message_latency.observe(time.perf_counter() - start)
