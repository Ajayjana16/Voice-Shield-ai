import { useRef, useState, useCallback, useEffect } from "react";

export function useSpeechRecognition({ onTranscript, onStatusChange, getTimestamp }) {
  const [isListening, setIsListening] = useState(false);
  const [confirmedText, setConfirmedText] = useState("");
  const [interimText, setInterimText] = useState("");
  const [segments, setSegments] = useState([]); // [{ id, time, text }]

  const recognitionRef = useRef(null);
  const isRunningRef = useRef(false);
  const isRestartingRef = useRef(false);
  const restartTimerRef = useRef(null);
  const restartRetryCountRef = useRef(0);

  // Persistent Text & Segment Accumulators across automatic recognition restarts
  const sessionBaseTextRef = useRef("");
  const instanceFinalTextRef = useRef("");
  const instanceFinalizedMapRef = useRef(new Map());
  const sessionSegmentsRef = useRef([]);

  const onTranscriptRef = useRef(onTranscript);
  const onStatusChangeRef = useRef(onStatusChange);
  const getTimestampRef = useRef(getTimestamp);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    onStatusChangeRef.current = onStatusChange;
  }, [onStatusChange]);

  useEffect(() => {
    getTimestampRef.current = getTimestamp;
  }, [getTimestamp]);

  const createRecognition = useCallback(() => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) return null;

    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.lang = navigator.language || "en-US";

    recognition.onstart = () => {
      setIsListening(true);
      restartRetryCountRef.current = 0;
      console.log(`[VoiceShield Debug] RECOGNITION_START at ${performance.now().toFixed(1)} ms`);
      if (window.__VOICE_SHIELD_TIMINGS__ && !window.__VOICE_SHIELD_TIMINGS__.T3) {
        const t3 = performance.now();
        window.__VOICE_SHIELD_TIMINGS__.T3 = t3;
        console.log(`[Latency Audit] T3: Web Speech API hardware ready in ${(t3 - (window.__VOICE_SHIELD_TIMINGS__.T2 || t3)).toFixed(1)} ms`);
      }
      if (onStatusChangeRef.current) onStatusChangeRef.current("listening");
    };

    recognition.onresult = (event) => {
      let currentInstanceFinal = "";
      let currentInterim = "";
      const currentInstanceSegments = [];

      for (let i = 0; i < event.results.length; ++i) {
        const res = event.results[i];
        const text = (res[0]?.transcript || "").trim();
        if (!text) continue;

        if (res.isFinal) {
          currentInstanceFinal += (currentInstanceFinal ? " " : "") + text;
          if (!instanceFinalizedMapRef.current.has(i)) {
            const timeStr = getTimestampRef.current ? getTimestampRef.current() : "00:00";
            instanceFinalizedMapRef.current.set(i, {
              id: `seg_${Date.now()}_${i}`,
              time: timeStr,
              text: text,
            });
          }
          currentInstanceSegments.push(instanceFinalizedMapRef.current.get(i));
        } else {
          currentInterim += (currentInterim ? " " : "") + text;
        }
      }

      instanceFinalTextRef.current = currentInstanceFinal;

      // Merge base history with current instance finalized + interim
      const fullConfirmed = (
        sessionBaseTextRef.current +
        (sessionBaseTextRef.current && currentInstanceFinal ? " " : "") +
        currentInstanceFinal
      ).trim();

      const fullTranscript = (
        fullConfirmed +
        (fullConfirmed && currentInterim ? " " : "") +
        currentInterim
      ).trim();

      const allSegments = [
        ...sessionSegmentsRef.current,
        ...currentInstanceSegments,
      ];

      setConfirmedText(fullConfirmed);
      setInterimText(currentInterim);
      setSegments(allSegments);

      if (onTranscriptRef.current) {
        onTranscriptRef.current(fullTranscript, currentInterim, fullConfirmed);
      }
    };

    recognition.onerror = (event) => {
      const err = event.error;
      // Recoverable browser audio/speech events: do not kill the session
      if (err === "no-speech" || err === "audio-capture" || err === "aborted" || err === "network") {
        return;
      }
      console.warn("Speech recognition notice:", err);
      if (err === "not-allowed" || err === "service-not-allowed") {
        isRunningRef.current = false;
        setIsListening(false);
        if (onStatusChangeRef.current) onStatusChangeRef.current("permission_denied");
      }
    };

    recognition.onend = () => {
      // 1. Commit finalized instance text and segments to persistent base
      if (instanceFinalTextRef.current) {
        sessionBaseTextRef.current = (
          sessionBaseTextRef.current +
          (sessionBaseTextRef.current ? " " : "") +
          instanceFinalTextRef.current
        ).trim();
        instanceFinalTextRef.current = "";
      }
      if (instanceFinalizedMapRef.current.size > 0) {
        sessionSegmentsRef.current = [
          ...sessionSegmentsRef.current,
          ...Array.from(instanceFinalizedMapRef.current.values()),
        ];
        instanceFinalizedMapRef.current.clear();
      }

      // 2. Clear transient interim text
      setInterimText("");

      // 3. Auto-restart if monitoring remains active
      if (isRunningRef.current) {
        safeRestart();
      } else {
        setIsListening(false);
        if (onStatusChangeRef.current) onStatusChangeRef.current("stopped");
      }
    };

    return recognition;
  }, []);

  const safeRestart = useCallback(() => {
    if (!isRunningRef.current) return;
    if (restartTimerRef.current) {
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }

    if (isRestartingRef.current) return;
    isRestartingRef.current = true;

    restartTimerRef.current = setTimeout(() => {
      isRestartingRef.current = false;
      if (!isRunningRef.current) return;

      try {
        if (recognitionRef.current) {
          try {
            recognitionRef.current.onstart = null;
            recognitionRef.current.onresult = null;
            recognitionRef.current.onerror = null;
            recognitionRef.current.onend = null;
            recognitionRef.current.abort();
          } catch {}
          recognitionRef.current = null;
        }

        const fresh = createRecognition();
        if (!fresh) return;

        recognitionRef.current = fresh;
        fresh.start();
        restartRetryCountRef.current = 0;
      } catch (e) {
        console.warn("Speech recognition restart attempt failed:", e);
        restartRetryCountRef.current += 1;
        if (isRunningRef.current && restartRetryCountRef.current <= 10) {
          const backoffMs = Math.min(1000, 80 * Math.pow(1.4, restartRetryCountRef.current));
          restartTimerRef.current = setTimeout(() => {
            if (isRunningRef.current) {
              safeRestart();
            }
          }, backoffMs);
        }
      }
    }, 60);
  }, [createRecognition]);

  const start = useCallback(() => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      console.warn("Browser SpeechRecognition not supported in this browser.");
      if (onStatusChangeRef.current) onStatusChangeRef.current("unsupported");
      return;
    }

    try {
      if (restartTimerRef.current) {
        clearTimeout(restartTimerRef.current);
        restartTimerRef.current = null;
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.onstart = null;
          recognitionRef.current.onresult = null;
          recognitionRef.current.onerror = null;
          recognitionRef.current.onend = null;
          recognitionRef.current.abort();
        } catch {}
        recognitionRef.current = null;
      }

      // Wipe all previous session text completely
      sessionBaseTextRef.current = "";
      sessionSegmentsRef.current = [];
      instanceFinalTextRef.current = "";
      instanceFinalizedMapRef.current.clear();
      setConfirmedText("");
      setInterimText("");
      setSegments([]);

      isRunningRef.current = true;
      restartRetryCountRef.current = 0;

      const recognition = createRecognition();
      if (!recognition) return;

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.warn("SpeechRecognition start exception:", err);
      setIsListening(false);
      isRunningRef.current = false;
    }
  }, [createRecognition]);

  const stop = useCallback(() => {
    isRunningRef.current = false;
    if (restartTimerRef.current) {
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.onstart = null;
        recognitionRef.current.onresult = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.onend = null;
        recognitionRef.current.abort();
      } catch {}
      recognitionRef.current = null;
    }
    setIsListening(false);

    // Commit any active interim text into confirmed segments on stop
    setInterimText((curInterim) => {
      if (curInterim && curInterim.trim()) {
        const timeStr = getTimestampRef.current ? getTimestampRef.current() : "00:00";
        const finalTrimmed = curInterim.trim();
        sessionBaseTextRef.current = (
          sessionBaseTextRef.current +
          (sessionBaseTextRef.current ? " " : "") +
          finalTrimmed
        ).trim();
        setConfirmedText(sessionBaseTextRef.current);
        setSegments((prev) => [
          ...prev,
          { id: `seg_end_${Date.now()}`, time: timeStr, text: finalTrimmed },
        ]);
      }
      return "";
    });
  }, []);

  const reset = useCallback(() => {
    sessionBaseTextRef.current = "";
    sessionSegmentsRef.current = [];
    instanceFinalTextRef.current = "";
    instanceFinalizedMapRef.current.clear();
    setConfirmedText("");
    setInterimText("");
    setSegments([]);
  }, []);

  const getTranscript = useCallback(() => {
    return (
      sessionBaseTextRef.current +
      (sessionBaseTextRef.current && instanceFinalTextRef.current ? " " : "") +
      instanceFinalTextRef.current
    ).trim() || confirmedText || "";
  }, [confirmedText]);

  useEffect(() => {
    return () => {
      isRunningRef.current = false;
      if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.onstart = null;
          recognitionRef.current.onresult = null;
          recognitionRef.current.onerror = null;
          recognitionRef.current.onend = null;
          recognitionRef.current.abort();
        } catch {}
        recognitionRef.current = null;
      }
    };
  }, []);

  return {
    isListening,
    confirmedText,
    interimText,
    segments,
    start,
    stop,
    reset,
    getTranscript,
  };
}

