from collections import deque
from typing import Deque

from app.models.schemas import RollingAnalysisStats


class ChunkStreamAggregator:
    """
    Maintains rolling state across live audio chunks:
    - Exponential moving average smoothing for noisy single-chunk predictions
    - Maximum peak risk tracking
    - Risk trajectory trend estimation
    - Chunk latency tracking
    - Ignores silent / non-speech chunks to avoid false high-risk spikes
    """

    def __init__(self, max_history: int = 20, ema_alpha: float = 0.35):
        self.max_history = max_history
        self.ema_alpha = ema_alpha
        self.history: Deque[int] = deque(maxlen=max_history)
        self.rolling_ema: float = 0.0
        self.chunk_count: int = 0

    def update(self, current_risk_score: int | None, latency_ms: float = 0.0) -> RollingAnalysisStats:
        self.chunk_count += 1

        if current_risk_score is None:
            # Silent or non-speech chunk: Do not distort rolling EMA or create false alerts
            return RollingAnalysisStats(
                latest_score=None,
                rolling_average=round(self.rolling_ema, 1),
                max_recent_risk=max(self.history) if self.history else 0,
                chunk_count=self.chunk_count,
                trend="WAITING_FOR_SPEECH",
                latency_ms=round(latency_ms, 2),
            )

        self.history.append(current_risk_score)

        if len(self.history) == 1:
            self.rolling_ema = float(current_risk_score)
        else:
            self.rolling_ema = self.ema_alpha * current_risk_score + (1.0 - self.ema_alpha) * self.rolling_ema

        # Max risk over last 5 chunks
        recent_window = list(self.history)[-5:]
        max_recent = max(recent_window) if recent_window else current_risk_score

        # Trend estimation
        if len(self.history) >= 3:
            prev_avg = sum(list(self.history)[-3:-1]) / 2.0
            diff = current_risk_score - prev_avg
            if diff > 8:
                trend = "RISING"
            elif diff < -8:
                trend = "FALLING"
            else:
                trend = "STABLE"
        else:
            trend = "STABLE"

        return RollingAnalysisStats(
            latest_score=current_risk_score,
            rolling_average=round(self.rolling_ema, 1),
            max_recent_risk=max_recent,
            chunk_count=self.chunk_count,
            trend=trend,
            latency_ms=round(latency_ms, 2),
        )

    def reset(self) -> None:
        self.history.clear()
        self.rolling_ema = 0.0
        self.chunk_count = 0


# Global session aggregator instance for live streams
live_stream_aggregator = ChunkStreamAggregator()
