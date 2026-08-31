import { useEffect, useState } from "react";
import { WS_URL } from "../services/api";

export function useLiveAnalysis() {
  const [isConnected, setIsConnected] = useState(false);
  const [latest, setLatest] = useState(null);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    socket.addEventListener("open", () => {
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
    socket.addEventListener("close", () => setIsConnected(false));
    socket.addEventListener("error", () => setIsConnected(false));
    return () => socket.close();
  }, []);

  return { isConnected, latest };
}
