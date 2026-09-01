import React, { useEffect, useRef, memo } from "react";

function WaveformComponent({ analyser = null, isLive = false, audioLevel = 0, score = 0 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let frameId;
    let fallbackPhase = 0;

    const bufferLength = analyser ? analyser.frequencyBinCount : 64;
    const dataArray = analyser ? new Uint8Array(bufferLength) : null;

    const render = () => {
      const { width, height } = canvas;
      ctx.clearRect(0, 0, width, height);

      // Light background
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, width, height);

      // Subtle horizontal centerline
      ctx.beginPath();
      ctx.strokeStyle = "#e2e8f0";
      ctx.lineWidth = 1;
      ctx.moveTo(0, height / 2);
      ctx.lineTo(width, height / 2);
      ctx.stroke();

      const centerY = height / 2;
      const bars = 48;
      const barWidth = width / bars;

      if (analyser && isLive) {
        // Real microphone data from Web Audio Analyser
        analyser.getByteFrequencyData(dataArray);

        // Calculate dynamic bar heights from actual frequency spectrum
        const step = Math.floor(bufferLength / bars) || 1;

        for (let i = 0; i < bars; i++) {
          const dataIndex = Math.min(i * step, bufferLength - 1);
          const rawValue = dataArray[dataIndex] || 0; // 0 - 255
          const normalized = rawValue / 255.0;

          // Scale with actual audio level
          const barHeight = Math.max(3, normalized * (height * 0.75) + (audioLevel > 0.05 ? 4 : 1));
          const x = i * barWidth;

          // Color based on active voice vs silence
          if (audioLevel > 0.08) {
            ctx.fillStyle = "#2563eb"; // Blue for active speech
          } else {
            ctx.fillStyle = "#94a3b8"; // Slate for background silence
          }

          ctx.fillRect(x + barWidth * 0.2, centerY - barHeight / 2, barWidth * 0.6, barHeight);
        }
      } else if (isLive) {
        // Fallback live indicator when analyser is initializing
        const amplitude = Math.max(4, audioLevel * (height * 0.6));
        for (let i = 0; i < bars; i++) {
          const x = i * barWidth;
          const normalized = Math.sin((i / bars) * Math.PI * 4 + fallbackPhase);
          const barHeight = Math.max(3, Math.abs(normalized) * amplitude);

          ctx.fillStyle = audioLevel > 0.08 ? "#2563eb" : "#94a3b8";
          ctx.fillRect(x + barWidth * 0.2, centerY - barHeight / 2, barWidth * 0.6, barHeight);
        }
        fallbackPhase += 0.08;
      } else {
        // Static resting baseline
        for (let i = 0; i < bars; i++) {
          const x = i * barWidth;
          ctx.fillStyle = "#cbd5e1";
          ctx.fillRect(x + barWidth * 0.2, centerY - 2, barWidth * 0.6, 4);
        }
      }

      frameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [analyser, isLive, audioLevel, score]);

  return (
    <div className="real-waveform-card" style={{ borderRadius: "8px", overflow: "hidden", border: "1px solid #e2e8f0" }}>
      <canvas ref={canvasRef} width={500} height={76} style={{ display: "block", width: "100%", height: "76px" }} />
    </div>
  );
}

export const Waveform = memo(WaveformComponent);
