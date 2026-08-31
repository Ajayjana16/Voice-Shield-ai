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

  const onTranscriptRef = useRef(onTranscript);
  const onStatusChangeRef = useRef(onStatusChange);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    onStatusChangeRef.current = onStatusChange;
  }, [onStatusChange]);

  const start = useCallback(() => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      console.warn("Browser SpeechRecognition not supported in this browser.");
      if (onStatusChangeRef.current) onStatusChangeRef.current("unsupported");
      return;
    }

    try {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {}
      }

      accumulatedFinalRef.current = "";
      setConfirmedText("");
      setInterimText("");

      const recognition = new Recognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      recognition.lang = "en-IN";

      recognition.onstart = () => {
        setIsListening(true);
        isRunningRef.current = true;
        if (onStatusChangeRef.current) onStatusChangeRef.current("listening");
      };

      recognition.onresult = (event) => {
        let currentInterim = "";
        let newFinal = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const trans = event.results[i][0]?.transcript || "";
          if (event.results[i].isFinal) {
            newFinal += " " + trans;
          } else {
            currentInterim += " " + trans;
          }
        }

        if (newFinal.trim()) {
          accumulatedFinalRef.current = appendFinalSegment(accumulatedFinalRef.current, newFinal);
          setConfirmedText(accumulatedFinalRef.current);
        }

        const trimmedInterim = currentInterim.trim();
        setInterimText(trimmedInterim);

        const fullTranscript = accumulatedFinalRef.current
          ? trimmedInterim
            ? `${accumulatedFinalRef.current} ${trimmedInterim}`
            : accumulatedFinalRef.current
          : trimmedInterim;

        if (onTranscriptRef.current) {
          onTranscriptRef.current(fullTranscript, trimmedInterim, accumulatedFinalRef.current);
        }
      };

      recognition.onerror = (event) => {
        console.warn("Speech recognition notice:", event.error);
        if (event.error === "not-allowed") {
          setIsListening(false);
          isRunningRef.current = false;
          if (onStatusChangeRef.current) onStatusChangeRef.current("permission_denied");
        }
      };

      recognition.onend = () => {
        if (isRunningRef.current) {
          try {
            recognition.start();
          } catch {
            setIsListening(false);
            isRunningRef.current = false;
          }
        } else {
          setIsListening(false);
          if (onStatusChangeRef.current) onStatusChangeRef.current("stopped");
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.warn("SpeechRecognition start exception:", err);
      setIsListening(false);
      isRunningRef.current = false;
    }
  }, []);

  const stop = useCallback(() => {
    isRunningRef.current = false;
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }
    setIsListening(false);
    setInterimText("");
  }, []);

  const reset = useCallback(() => {
    accumulatedFinalRef.current = "";
    setConfirmedText("");
    setInterimText("");
  }, []);

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
  };
}

