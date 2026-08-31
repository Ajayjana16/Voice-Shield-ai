import React, { useState } from "react";
import { Shield, Radio, Activity, History, BookOpen, Lock, Menu, X, Server, Home } from "lucide-react";

export function Navbar({ currentPath, onNavigate, health, activeModel, isFallback }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { label: "Home", path: "/", icon: Home },
    { label: "Analyze", path: "/analyze", icon: Activity },
    { label: "Live Monitor", path: "/live", icon: Radio },
    { label: "History", path: "/history", icon: History },
    { label: "How It Works", path: "/how-it-works", icon: BookOpen },
    { label: "Security", path: "/security", icon: Lock },
  ];

  const handleNav = (path) => {
    onNavigate(path);
    setMobileMenuOpen(false);
  };

  const isOnline = health === "online";

  return (
    <header className="global-navbar">
      <div className="nav-container">
        {/* Brand */}
        <div className="nav-brand" onClick={() => handleNav("/")} role="button" tabIndex={0}>
          <div className="brand-logo-shield">
            <Shield size={18} />
          </div>
          <div className="brand-text-col">
            <span className="brand-title-text">Voice Shield</span>
            <span className="brand-subtitle-text">Voice Security & Scam Detection</span>
          </div>
        </div>

        {/* Desktop Nav Links */}
        <nav className="desktop-nav nav-links-row" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPath === item.path;
            return (
              <button
                key={item.path}
                className={`nav-link-btn ${isActive ? "active-link" : ""}`}
                onClick={() => handleNav(item.path)}
              >
                <div className="flex items-center gap-1.5">
                  <Icon size={13} />
                  <span>{item.label}</span>
                </div>
              </button>
            );
          })}
        </nav>

        {/* Desktop Actions & Status */}
        <div className="desktop-actions nav-actions-group">
          <div className="status-cluster-nav">
            <span className={`nav-status-tag ${isOnline ? "tag-online" : "tag-offline"}`}>
              <Server size={11} />
              <span>{isOnline ? "API Online" : "API Offline"}</span>
            </span>
          </div>

          <button className="nav-cta-btn" onClick={() => handleNav("/analyze")}>
            <Activity size={13} />
            <span>Analyze a Call</span>
          </button>
        </div>

        {/* Mobile Toggle Button */}
        <button
          className="mobile-menu-toggle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="mobile-drawer-menu">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPath === item.path;
            return (
              <button
                key={item.path}
                className={`mobile-nav-btn ${isActive ? "mobile-active" : ""}`}
                onClick={() => handleNav(item.path)}
              >
                <div className="flex items-center gap-2">
                  <Icon size={15} />
                  <span>{item.label}</span>
                </div>
              </button>
            );
          })}
          <div className="mobile-drawer-footer">
            <span className={`nav-status-tag ${isOnline ? "tag-online" : "tag-offline"}`}>
              <Server size={11} />
              <span>{isOnline ? "API Online" : "API Offline"}</span>
            </span>
            <button className="nav-cta-btn w-full justify-center mt-2" onClick={() => handleNav("/analyze")}>
              <Activity size={13} />
              <span>Analyze a Call</span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
