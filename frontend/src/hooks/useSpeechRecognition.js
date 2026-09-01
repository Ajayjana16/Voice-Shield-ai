import { useRef, useState, useCallback, useEffect } from "react";

function appendFinalSegment(existing, segment) {
  const ex = (existing || "").trim();

  const seg = (segment || "").trim();
  if (!seg) return ex;
  if (!ex) return seg;

  // Exact duplicate check
  if (ex.toLowerCase().endsWith(seg.toLowerCase())) return ex;

  // Overlap deduplication at boundary
  const wordsEx = ex.split(/\s+/);
  const wordsSeg = seg.split(/\s+/);
  let maxOverlap = 0;
  const maxCheck = Math.min(wordsEx.length, wordsSeg.length, 6);

  for (let k = 1; k <= maxCheck; k++) {
    const endSlice = wordsEx.slice(wordsEx.length - k).join(" ").toLowerCase();
    const startSlice = wordsSeg.slice(0, k).join(" ").toLowerCase();
    if (endSlice === startSlice) {
      maxOverlap = k;
    }
  }

  if (maxOverlap > 0) {
    const nonOverlapping = wordsSeg.slice(maxOverlap).join(" ");
    return nonOverlapping ? `${ex} ${nonOverlapping}` : ex;
  }
  return `${ex} ${seg}`;
}

export function useSpeechRecognition({ onTranscript, onStatusChange }) {
  const [isListening, setIsListening] = useState(false);
  const [confirmedText, setConfirmedText] = useState("");
  const [interimText, setInterimText] = useState("");
  const recognitionRef = useRef(null);
  const isRunningRef = useRef(false);
  const accumulatedFinalRef = useRef("");
  const restartTimerRef = useRef(null);

  const onTranscriptRef = useRef(onTranscript);
  const onStatusChangeRef = useRef(onStatusChange);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    onStatusChangeRef.current = onStatusChange;
  }, [onStatusChange]);

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
      let currentInterim = "";
      let newlyFinalized = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const trans = event.results[i][0]?.transcript || "";
        if (event.results[i].isFinal) {
          newlyFinalized += " " + trans;
        } else {
          currentInterim += " " + trans;
        }
      }

      const trimmedFinal = newlyFinalized.trim();
      if (trimmedFinal) {
        accumulatedFinalRef.current = appendFinalSegment(accumulatedFinalRef.current, trimmedFinal);
        setConfirmedText(accumulatedFinalRef.current);
      }

      const trimmedInterim = currentInterim.trim();
      setInterimText(trimmedInterim);

      if (trimmedInterim || trimmedFinal) {
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

      const fullTranscript = accumulatedFinalRef.current
        ? trimmedInterim
          ? `${accumulatedFinalRef.current} ${trimmedInterim}`
          : accumulatedFinalRef.current
        : trimmedInterim;

      if (onTranscriptRef.current) {
        onTranscriptRef.current(fullTranscript, trimmedInterim, accumulatedFinalRef.current, trimmedFinal || null);
      }
    };

    recognition.onerror = (event) => {
      // Ignorable transient events
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
      if (isRunningRef.current) {
        if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
        restartTimerRef.current = setTimeout(() => {
          if (isRunningRef.current) {
            try {
              if (recognitionRef.current) {
                recognitionRef.current.start();
              }
            } catch {
              try {
                const fresh = createRecognition();
                if (fresh) {
                  recognitionRef.current = fresh;
                  fresh.start();
                }
              } catch {}
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

      accumulatedFinalRef.current = "";
      setConfirmedText("");
      setInterimText("");
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
    // Commit any remaining interim text into confirmed text before clearing interimText
    setInterimText((curInterim) => {
      if (curInterim && curInterim.trim()) {
        accumulatedFinalRef.current = appendFinalSegment(accumulatedFinalRef.current, curInterim);
        setConfirmedText(accumulatedFinalRef.current);
      }
      return "";
    });
  }, []);

  const reset = useCallback(() => {
    accumulatedFinalRef.current = "";
    setConfirmedText("");
    setInterimText("");
  }, []);

  const getTranscript = useCallback(() => {
    return accumulatedFinalRef.current || confirmedText || "";
  }, [confirmedText]);

  useEffect(() => {
    return () => {
      isRunningRef.current = false;
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
    start,
    stop,
    reset,
    getTranscript,
  };
}

