from app.services.audio.chunk_processor import ChunkStreamAggregator


def test_chunk_stream_aggregator_ema_and_trend():
    aggregator = ChunkStreamAggregator(max_history=10, ema_alpha=0.4)

    # Initial chunk
    stats1 = aggregator.update(current_risk_score=20, latency_ms=15.2)
    assert stats1.chunk_count == 1
    assert stats1.latest_score == 20
    assert stats1.rolling_average == 20.0
    assert stats1.max_recent_risk == 20
    assert stats1.trend == "STABLE"

    # Rising stream
    aggregator.update(current_risk_score=35, latency_ms=16.0)
    stats3 = aggregator.update(current_risk_score=75, latency_ms=14.8)
    assert stats3.chunk_count == 3
    assert stats3.latest_score == 75
    assert stats3.max_recent_risk == 75
    assert stats3.trend == "RISING"
    assert stats3.rolling_average > 20.0

    # Falling stream
    aggregator.update(current_risk_score=20, latency_ms=15.0)
    stats5 = aggregator.update(current_risk_score=15, latency_ms=15.0)
    assert stats5.trend == "FALLING"

    # Reset
    aggregator.reset()
    assert aggregator.chunk_count == 0
    assert len(aggregator.history) == 0

