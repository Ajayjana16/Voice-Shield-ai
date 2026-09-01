import { useEffect, useState, useRef, useCallback } from "react";
import { WS_URL } from "../services/api";

const INITIAL_RETRY_DELAY_MS = 2000;
const MAX_RETRY_DELAY_MS = 30000;
const MAX_RETRIES = 8;

export function useLiveAnalysis() {
  const [isConnected, setIsConnected] = useState(false);
  const [latest, setLatest] = useState(null);

  const socketRef = useRef(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef(null);
  const unmountedRef = useRef(false);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;
    if (socketRef.current && socketRef.current.readyState < 2) {
      // Already open or connecting
      return;
    }

    try {
      const socket = new WebSocket(WS_URL);
      socketRef.current = socket;

      socket.addEventListener("open", () => {
        if (unmountedRef.current) { socket.close(); return; }
        retryCountRef.current = 0;
        setIsConnected(true);
        socket.send("dashboard-connected");
      });

      socket.addEventListener("message", (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "analysis" || message.type === "chunk") {
            setLatest(message.payload);
          }
        } catch (err) {
          console.warn("WebSocket parse error:", err);
        }
      });

      socket.addEventListener("close", () => {
        if (unmountedRef.current) return;
        setIsConnected(false);
        scheduleReconnect();
      });

      socket.addEventListener("error", () => {
        // error is always followed by close; let the close handler reschedule
        setIsConnected(false);
      });
    } catch (err) {
      // WebSocket constructor can throw if WS_URL is invalid
      console.warn("[VoiceShield] WebSocket construction failed:", err);
      scheduleReconnect();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const scheduleReconnect = useCallback(() => {
    if (unmountedRef.current) return;
    if (retryCountRef.current >= MAX_RETRIES) {
      console.warn("[VoiceShield] WebSocket max retries reached. Will not reconnect automatically.");
      return;
    }

    const delay = Math.min(
      INITIAL_RETRY_DELAY_MS * Math.pow(2, retryCountRef.current),
      MAX_RETRY_DELAY_MS
    );
    retryCountRef.current += 1;
    console.log(`[VoiceShield] WebSocket reconnecting in ${delay}ms (attempt ${retryCountRef.current})`);

    if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    retryTimerRef.current = setTimeout(() => {
      if (!unmountedRef.current) connect();
    }, delay);
  }, [connect]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();

    return () => {
      unmountedRef.current = true;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [connect]);

  return { isConnected, latest };
}
