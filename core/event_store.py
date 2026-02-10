# -*- coding: utf-8 -*-
"""
Event Store - Audit trail e event sourcing
Persiste eventos (mensagem enviada, recebida, plano executado) para debug e replay.

Autor: JARVIS Team
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Um evento no audit trail."""
    event_type: str  # 'whatsapp_sent', 'message_received', 'plan_executed', etc.
    timestamp: datetime
    user_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Event":
        ts = d.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return cls(
            event_type=d.get("event_type", ""),
            timestamp=ts or datetime.now(),
            user_id=d.get("user_id"),
            data=d.get("data"),
        )


class EventStore:
    """Armazena eventos em arquivo JSONL para audit e replay."""

    def __init__(self, events_dir: Optional[Path] = None):
        if events_dir is None:
            events_dir = Path(__file__).resolve().parent.parent / "data" / "events"
        self.events_dir = Path(events_dir)
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self._current_file = self.events_dir / "events.jsonl"

    def append(self, event: Event) -> None:
        """Adiciona um evento ao log (append em JSONL)."""
        try:
            line = json.dumps(event.to_dict(), ensure_ascii=False, default=str) + "\n"
            with open(self._current_file, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError as e:
            logger.warning("EventStore.append falhou: %s", e)

    def replay_events(self, since: Optional[datetime] = None) -> List[Event]:
        """Lê eventos desde 'since' (ordem cronológica). Reconstrói estado a partir de eventos."""
        if not self._current_file.exists():
            return []
        events = []
        try:
            for line in self._current_file.read_text(encoding="utf-8").strip().splitlines():
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    ev = Event.from_dict(d)
                    if since is None or ev.timestamp >= since:
                        events.append(ev)
                except (json.JSONDecodeError, KeyError):
                    continue
        except OSError as e:
            logger.warning("EventStore.replay_events falhou: %s", e)
        return events
