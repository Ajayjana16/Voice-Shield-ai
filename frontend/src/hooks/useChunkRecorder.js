import { useRef, useState, useCallback, useEffect } from "react";

export function useChunkRecorder({ onChunk }) {
  const [isLive, setIsLive] = useState(false);
  const [speechActivity, setSpeechActivity] = useState("idle"); // 'idle' | 'listening' | 'speaking'
  const [audioLevel, setAudioLevel] = useState(0); // 0.0 to 1.0
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animFrameRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const accumulatedChunksRef = useRef([]);

  // Audio level and VAD monitor
  const startAudioAnalysis = useCallback((stream) => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.6;
      source.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      const checkLevel = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        const normalized = Math.min(1.0, avg / 80); // 0 to 1
        setAudioLevel(normalized);

        // VAD threshold
        if (normalized > 0.08) {
          setSpeechActivity("speaking");
        } else {
          setSpeechActivity("listening");
        }

        animFrameRef.current = requestAnimationFrame(checkLevel);
      };

      checkLevel();
    } catch (e) {
      console.warn("Web Audio Analyser unavailable:", e);
    }
  }, []);

  const onChunkRef = useRef(onChunk);
  useEffect(() => {
    onChunkRef.current = onChunk;
  }, [onChunk]);

  const sessionStartTimeRef = useRef(null);

  const start = useCallback(async () => {
    try {
      accumulatedChunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      streamRef.current = stream;
      startAudioAnalysis(stream);

      // Determine supported mimeType
      let mimeType = "audio/webm;codecs=opus";
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : MediaRecorder.isTypeSupported("audio/mp4")
          ? "audio/mp4"
          : "";
      }

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      recorderRef.current = recorder;

      recorder.ondataavailable = async (event) => {
        if (event.data && event.data.size > 0) {
          accumulatedChunksRef.current.push(event.data);
          const chunkFile = new File(
            [event.data],
            `live-chunk-${Date.now()}.${mimeType.includes("mp4") ? "mp4" : "webm"}`,
            { type: event.data.type || "audio/webm" }
          );
          if (onChunkRef.current) {
            await onChunkRef.current(chunkFile);
          }
        }
      };

      // 2-second streaming chunks
      recorder.start(2000);
      setIsLive(true);
      
      sessionStartTimeRef.current = Date.now();
      setElapsedSeconds(0);

      // High-precision wall-clock timer using persistent session start time
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
      timerIntervalRef.current = setInterval(() => {
        if (sessionStartTimeRef.current) {
          const secs = Math.max(0, Math.floor((Date.now() - sessionStartTimeRef.current) / 1000));
          setElapsedSeconds(secs);
        }
      }, 500);
    } catch (err) {
      console.error("Microphone access failed:", err);
      throw err;
    }
  }, [startAudioAnalysis]);

  const stop = useCallback(() => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }

    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
    }


    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    analyserRef.current = null;

    setIsLive(false);
    setSpeechActivity("idle");
    setAudioLevel(0);

    // Create complete recorded file from all accumulated chunks
    const chunks = accumulatedChunksRef.current;
    if (chunks.length > 0) {
      const mime = chunks[0].type || "audio/webm";
      const fullBlob = new Blob(chunks, { type: mime });
      const ext = mime.includes("mp4") ? "mp4" : "webm";
      return new File([fullBlob], `recorded-call-${Date.now()}.${ext}`, { type: mime });
    }
    return null;
  }, []);

  useEffect(() => {
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (audioContextRef.current && audioContextRef.current.state !== "closed") {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, []);

  const resetTimer = useCallback(() => {
    setElapsedSeconds(0);
    sessionStartTimeRef.current = null;
  }, []);

  return {
    isLive,
    speechActivity,
    audioLevel,
    elapsedSeconds,
    sessionStartTime: sessionStartTimeRef.current,
    analyser: analyserRef.current,
    start,
    stop,
    resetTimer,
  };
}

