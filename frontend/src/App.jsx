import React, { useEffect, useState } from "react";
import { Navbar } from "./components/Navbar";
import { Footer } from "./components/Footer";
import { LandingPage } from "./pages/LandingPage";
import { AnalyzePage } from "./pages/AnalyzePage";
import { LiveMonitorPage } from "./pages/LiveMonitorPage";
import { HowItWorksPage } from "./pages/HowItWorksPage";
import { HistoryPage } from "./pages/HistoryPage";
import { SecurityInfoPage } from "./pages/SecurityInfoPage";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { useLiveAnalysis } from "./hooks/useLiveAnalysis";
import { getHealth } from "./services/api";

const VALID_ROUTES = ["/", "/analyze", "/live", "/live-monitoring", "/how-it-works", "/history", "/security"];

export default function App() {
  const [currentPath, setCurrentPath] = useState(() => {
    const p = window.location.pathname;
    return VALID_ROUTES.includes(p) ? p : "/";
  });
  const [health, setHealth] = useState("checking");
  const [healthInfo, setHealthInfo] = useState(null);

  const { isConnected } = useLiveAnalysis();

  useEffect(() => {
    // Sync browser back/forward buttons
    const onPopState = () => {
      const p = window.location.pathname;
      setCurrentPath(VALID_ROUTES.includes(p) ? p : "/");
    };
    window.addEventListener("popstate", onPopState);

    // Initial Health Check
    getHealth()
      .then((data) => {
        setHealth("online");
        setHealthInfo(data);
      })
      .catch(() => setHealth("offline"));

    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function handleNavigate(path) {
    if (path !== currentPath) {
      window.history.pushState({}, "", path);
      setCurrentPath(path);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  const isFallback =
    healthInfo?.deepfake_model_status === "heuristic_fallback_active" ||
    healthInfo?.deepfake_model_status === "model_failed";

  return (
    <div className="app-root">
      {/* Global Header */}
      <Navbar
        currentPath={currentPath}
        onNavigate={handleNavigate}
        health={health}
        activeModel={healthInfo?.model_name || "MelodyMachine"}
        isFallback={isFallback}
      />

      {/* Main Page Routing */}
      <main className="page-content-host">
        <ErrorBoundary onReset={() => handleNavigate("/analyze")}>
          {currentPath === "/" && <LandingPage onNavigate={handleNavigate} />}
          {currentPath === "/analyze" && <AnalyzePage onNavigate={handleNavigate} />}
          {(currentPath === "/live" || currentPath === "/live-monitoring") && (
            <LiveMonitorPage onNavigate={handleNavigate} />
          )}

          {currentPath === "/how-it-works" && <HowItWorksPage onNavigate={handleNavigate} />}
          {currentPath === "/history" && <HistoryPage onNavigate={handleNavigate} />}
          {currentPath === "/security" && <SecurityInfoPage onNavigate={handleNavigate} />}
        </ErrorBoundary>
      </main>

      {/* Global Footer */}
      <Footer onNavigate={handleNavigate} />
    </div>
  );
}

