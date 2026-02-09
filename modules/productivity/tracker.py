# -*- coding: utf-8 -*-
"""Rastreador de sessões de trabalho/foco."""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class ActivityRecord:
    category: str
    start: datetime
    end: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        end = self.end or datetime.now()
        return (end - self.start).total_seconds()


class ProductivityTracker:
    def __init__(self):
        self._sessions: List[ActivityRecord] = []
        self._current: Optional[ActivityRecord] = None
        self._max_sessions = 1000

    def start_session(self, category: str = 'work', metadata: Optional[Dict] = None) -> ActivityRecord:
        if self._current:
            self.end_session()
        self._current = ActivityRecord(category=category, start=datetime.now(), metadata=metadata or {})
        return self._current

    def end_session(self) -> Optional[ActivityRecord]:
        if not self._current:
            return None
        self._current.end = datetime.now()
        self._sessions.append(self._current)
        if len(self._sessions) > self._max_sessions:
            self._sessions.pop(0)
        record = self._current
        self._current = None
        return record

    def get_today_summary(self) -> Dict[str, Any]:
        today = datetime.now().date()
        by_category = defaultdict(float)
        for s in self._sessions:
            if s.start.date() == today and s.end:
                by_category[s.category] += s.duration_seconds
        total = sum(by_category.values())
        return {
            'date': today.isoformat(), 'total_seconds': total, 'total_hours': round(total / 3600, 2),
            'by_category': dict(by_category), 'session_count': len([s for s in self._sessions if s.start.date() == today])
        }

    def get_week_summary(self) -> Dict[str, Any]:
        week_ago = datetime.now() - timedelta(days=7)
        recent = [s for s in self._sessions if s.start >= week_ago and s.end]
        by_category = defaultdict(float)
        by_day = defaultdict(float)
        for s in recent:
            by_category[s.category] += s.duration_seconds
            by_day[s.start.date().isoformat()] += s.duration_seconds
        total = sum(by_category.values())
        return {
            'total_seconds': total, 'total_hours': round(total / 3600, 2),
            'by_category': dict(by_category), 'by_day': dict(by_day), 'session_count': len(recent)
        }

    def get_current_session(self) -> Optional[ActivityRecord]:
        return self._current
