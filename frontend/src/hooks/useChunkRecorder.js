import { useRef, useState, useCallback, useEffect } from "react";

// Mobile-safe audio constraints with fallback
export async function getMobileSafeMicrophoneStream(deviceId) {
  if (typeof window === "undefined") {
    throw new Error("WINDOW_UNAVAILABLE");
  }

  const hasMediaDevices = !!(navigator?.mediaDevices?.getUserMedia);
  const hasLegacyGetUserMedia = !!(navigator?.getUserMedia || navigator?.webkitGetUserMedia || navigator?.mozGetUserMedia);

  if (!hasMediaDevices && !hasLegacyGetUserMedia) {
    throw new Error("MEDIA_DEVICES_UNSUPPORTED");
  }

  const audioConstraints = {
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
  };
  if (deviceId) {
    audioConstraints.deviceId = { exact: deviceId };
  }

  // 1. Attempt with standard optimized constraints
  if (hasMediaDevices) {
    try {
      console.log("[VoiceShield Mic] Requesting microphone with preferred constraints...");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
      console.log("[VoiceShield Mic] Microphone access granted with preferred constraints.");
      return stream;
    } catch (prefErr) {
      console.warn("[VoiceShield Mic] Preferred constraints rejected, falling back to basic audio constraints:", prefErr);
    }

    // 2. Fallback to basic audio: true (essential on many mobile browsers)
    try {
      const basicConstraints = deviceId ? { audio: { deviceId: { exact: deviceId } } } : { audio: true };
      const stream = await navigator.mediaDevices.getUserMedia(basicConstraints);
      console.log("[VoiceShield Mic] Microphone access granted with basic constraints fallback.");
      return stream;
    } catch (basicErr) {
      console.error("[VoiceShield Mic] Basic constraints request failed:", basicErr);
      throw basicErr;
    }
  }

  // 3. Legacy getUserMedia fallback for older mobile browsers
  const legacyGetUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
  return new Promise((resolve, reject) => {
    legacyGetUserMedia.call(navigator, { audio: true }, resolve, reject);
  });
}

// Check if an audio track is currently active and producing sound
export function isAudioTrackActive(stream) {
  if (!stream) return false;
  const tracks = stream.getAudioTracks();
  if (!tracks || tracks.length === 0) return false;
  const track = tracks[0];
  return track.readyState === "live" && track.enabled;
}

export function useChunkRecorder({ onChunk }) {
  const [isLive, setIsLive] = useState(false);
  const [speechActivity, setSpeechActivity] = useState("idle"); // 'idle' | 'listening' | 'speaking'
  const [audioLevel, setAudioLevel] = useState(0); // 0.0 to 1.0
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const sourceNodeRef = useRef(null);
  const animFrameRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const accumulatedChunksRef = useRef([]);

  // Mobile AudioContext Resume helper
  const resumeAudioContext = useCallback(async () => {
    try {
      if (audioContextRef.current && audioContextRef.current.state === "suspended") {
        console.log("[VoiceShield Audio] Resuming suspended AudioContext on mobile...");
        await audioContextRef.current.resume();
        console.log("[VoiceShield Audio] AudioContext resumed successfully. State:", audioContextRef.current.state);
      }
    } catch (e) {
      console.warn("[VoiceShield Audio] AudioContext resume notice:", e);
    }
  }, []);

  // Audio level and VAD monitor
  const startAudioAnalysis = useCallback(async (stream) => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) {
        console.warn("[VoiceShield Audio] Web Audio API is not supported in this browser.");
        return;
      }

      // Close any previously hanging audio contexts
      if (audioContextRef.current && audioContextRef.current.state !== "closed") {
        try {
          await audioContextRef.current.close();
        } catch (_) {}
      }

      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;

      // Crucial on Mobile (iOS Safari & Android Chrome): AudioContext begins suspended
      if (audioCtx.state === "suspended") {
        try {
          await audioCtx.resume();
          console.log("[VoiceShield Audio] AudioContext state after initial resume:", audioCtx.state);
        } catch (resumeErr) {
          console.warn("[VoiceShield Audio] Initial resume attempt warning:", resumeErr);
        }
      }

      const source = audioCtx.createMediaStreamSource(stream);
      sourceNodeRef.current = source;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.6;
      source.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      let lastUpdateMs = 0;
      let lastActivity = "idle";

      const checkLevel = (now) => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);

        // Throttle React state updates to 10 FPS (every 100ms) unless state transitions
        if (now - lastUpdateMs > 100) {
          lastUpdateMs = now;
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / dataArray.length;
          const normalized = Math.min(1.0, avg / 80); // 0 to 1
          setAudioLevel(normalized);

          // VAD threshold for mobile/desktop microphones
          const newActivity = normalized > 0.06 ? "speaking" : "listening";
          if (newActivity !== lastActivity) {
            lastActivity = newActivity;
            setSpeechActivity(newActivity);
          }
        }

        animFrameRef.current = requestAnimationFrame(checkLevel);
      };

      animFrameRef.current = requestAnimationFrame(checkLevel);
    } catch (e) {
      console.warn("[VoiceShield Audio] Web Audio Analyser initialization notice:", e);
    }
  }, []);

  const onChunkRef = useRef(onChunk);
  useEffect(() => {
    onChunkRef.current = onChunk;
  }, [onChunk]);

  const sessionStartTimeRef = useRef(null);

  const start = useCallback(async (existingStream, deviceId) => {
    try {
      accumulatedChunksRef.current = [];
      const stream = existingStream || (await getMobileSafeMicrophoneStream(deviceId));

      if (!isAudioTrackActive(stream)) {
        throw new Error("AUDIO_TRACK_INACTIVE");
      }

      streamRef.current = stream;
      await startAudioAnalysis(stream);

      // Determine supported mimeType across Desktop & Mobile (iOS Safari requires audio/mp4)
      let selectedMimeType = "";
      if (typeof MediaRecorder !== "undefined") {
        const candidateTypes = [
          "audio/webm;codecs=opus",
          "audio/webm",
          "audio/mp4",
          "audio/aac",
          "audio/ogg",
        ];
        for (const t of candidateTypes) {
          if (MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(t)) {
            selectedMimeType = t;
            break;
          }
        }
      }

      console.log(`[VoiceShield Mic] Selected MediaRecorder MIME type: ${selectedMimeType || "browser default"}`);

      let recorder = null;
      try {
        recorder = new MediaRecorder(
          stream,
          selectedMimeType ? { mimeType: selectedMimeType } : undefined
        );
      } catch (recErr) {
        console.warn("[VoiceShield Mic] Fallback to default MediaRecorder without MIME config:", recErr);
        recorder = new MediaRecorder(stream);
      }
      recorderRef.current = recorder;

      recorder.ondataavailable = async (event) => {
        if (event.data && event.data.size > 0) {
          accumulatedChunksRef.current.push(event.data);
          const ext = (event.data.type && event.data.type.includes("mp4")) ? "mp4" : "webm";
          const chunkFile = new File(
            [event.data],
            `live-chunk-${Date.now()}.${ext}`,
            { type: event.data.type || "audio/webm" }
          );
          if (onChunkRef.current) {
            await onChunkRef.current(chunkFile);
          }
        }
      };

      // Start recorder with 2000ms chunks
      recorder.start(2000);
      setIsLive(true);

      sessionStartTimeRef.current = Date.now();
      setElapsedSeconds(0);

      // Wall-clock timer
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
      timerIntervalRef.current = setInterval(() => {
        if (sessionStartTimeRef.current) {
          const secs = Math.max(0, Math.floor((Date.now() - sessionStartTimeRef.current) / 1000));
          setElapsedSeconds(secs);
        }
      }, 500);

      return stream;
    } catch (err) {
      console.error("[VoiceShield Mic] Recorder start failed:", err);
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
      try {
        recorderRef.current.stop();
      } catch (_) {}
    }

    if (sourceNodeRef.current) {
      try {
        sourceNodeRef.current.disconnect();
      } catch (_) {}
      sourceNodeRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => {
        try {
          t.stop();
        } catch (_) {}
      });
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
    resumeAudioContext,
  };
}
