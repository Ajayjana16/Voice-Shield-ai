import { useRef, useState, useCallback, useEffect } from "react";

export function useSpeechRecognition({ onTranscript, onStatusChange, getTimestamp }) {
  const [isListening, setIsListening] = useState(false);
  const [confirmedText, setConfirmedText] = useState("");
  const [interimText, setInterimText] = useState("");
  const [segments, setSegments] = useState([]); // [{ id, time, text }]

  const recognitionRef = useRef(null);
  const isRunningRef = useRef(false);
  const restartTimerRef = useRef(null);
  const sessionBaseTextRef = useRef("");
  const sessionSegmentsRef = useRef([]);
  const instanceFinalTextRef = useRef("");
  const getTimestampRef = useRef(getTimestamp);

  const onTranscriptRef = useRef(onTranscript);
  const onStatusChangeRef = useRef(onStatusChange);

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
      if (window.__VOICE_SHIELD_TIMINGS__ && !window.__VOICE_SHIELD_TIMINGS__.T3) {
        const t3 = performance.now();
        window.__VOICE_SHIELD_TIMINGS__.T3 = t3;
        console.log(`[Latency Audit] T3: Web Speech API hardware ready in ${(t3 - (window.__VOICE_SHIELD_TIMINGS__.T2 || t3)).toFixed(1)} ms`);
      }
      if (onStatusChangeRef.current) onStatusChangeRef.current("listening");
    };

    recognition.onresult = (event) => {
      let instanceFinal = "";
      let currentInterim = "";
      const currentInstanceSegments = [];

      for (let i = 0; i < event.results.length; ++i) {
        const res = event.results[i];
        const text = (res[0]?.transcript || "").trim();
        if (!text) continue;

        if (res.isFinal) {
          instanceFinal += (instanceFinal ? " " : "") + text;
          const timeStr = getTimestampRef.current ? getTimestampRef.current() : "00:00";
          currentInstanceSegments.push({
            id: `inst_seg_${i}_${text.substring(0, 10)}`,
            time: timeStr,
            text: text,
          });
        } else {
          currentInterim += (currentInterim ? " " : "") + text;
        }
      }

      instanceFinalTextRef.current = instanceFinal;

      // Merge base history with current instance
      const fullConfirmed = (
        sessionBaseTextRef.current +
        (sessionBaseTextRef.current && instanceFinal ? " " : "") +
        instanceFinal
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

      // Latency instrumentation
      if (currentInterim || instanceFinal) {
        if (window.__VOICE_SHIELD_TIMINGS__ && !window.__VOICE_SHIELD_TIMINGS__.T4) {
          const t4 = performance.now();
          window.__VOICE_SHIELD_TIMINGS__.T4 = t4;
          const t0 = window.__VOICE_SHIELD_TIMINGS__.T0 || t4;
          const t1 = window.__VOICE_SHIELD_TIMINGS__.T1 || t4;
          const t2 = window.__VOICE_SHIELD_TIMINGS__.T2 || t4;
          const t3 = window.__VOICE_SHIELD_TIMINGS__.T3 || t4;

          requestAnimationFrame(() => {
            const t5 = performance.now();
            window.__VOICE_SHIELD_TIMINGS__.T5 = t5;
            console.log(`========================================
[VOICE SHIELD LATENCY AUDIT REPORT]
• T1 - T0 (Mic Permission / Acquisition) : ${(t1 - t0).toFixed(1)} ms
• T2 - T1 (Speech Recognition Launch)    : ${(t2 - t1).toFixed(1)} ms
• T3 - T2 (Web Speech Engine Handshake)  : ${(t3 - t2).toFixed(1)} ms
• T4 - T3 (Speech-to-First-Interim)      : ${(t4 - t3).toFixed(1)} ms
• T5 - T4 (React State -> DOM Render)    : ${(t5 - t4).toFixed(1)} ms
• Total T5 - T0 (Complete Startup Latency): ${(t5 - t0).toFixed(1)} ms
========================================`);
          });
        }
      }

      if (onTranscriptRef.current) {
        onTranscriptRef.current(fullTranscript, currentInterim, fullConfirmed);
      }
    };

    recognition.onerror = (event) => {
      if (event.error === "no-speech" || event.error === "audio-capture") {
        return;
      }
      console.warn("Speech recognition notice:", event.error);
      if (event.error === "not-allowed") {
        isRunningRef.current = false;
        setIsListening(false);
        if (onStatusChangeRef.current) onStatusChangeRef.current("permission_denied");
      }
    };

    recognition.onend = () => {
      // Commit current instance final text and segments into base history before next instance
      if (instanceFinalTextRef.current) {
        sessionBaseTextRef.current = (
          sessionBaseTextRef.current +
          (sessionBaseTextRef.current ? " " : "") +
          instanceFinalTextRef.current
        ).trim();
        instanceFinalTextRef.current = "";
      }

      if (isRunningRef.current) {
        if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
        restartTimerRef.current = setTimeout(() => {
          if (isRunningRef.current) {
            try {
              const fresh = createRecognition();
              if (fresh) {
                recognitionRef.current = fresh;
                fresh.start();
              }
            } catch (e) {
              console.warn("Speech recognition restart retry:", e);
            }
          }
        }, 50);
      } else {
        setIsListening(false);
        if (onStatusChangeRef.current) onStatusChangeRef.current("stopped");
      }
    };

    return recognition;
  }, []);

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
          recognitionRef.current.abort();
        } catch {}
      }

      sessionBaseTextRef.current = "";
      sessionSegmentsRef.current = [];
      instanceFinalTextRef.current = "";
      setConfirmedText("");
      setInterimText("");
      setSegments([]);
      isRunningRef.current = true;

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
        recognitionRef.current.stop();
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
          recognitionRef.current.stop();
        } catch {}
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

