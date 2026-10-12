"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function TopNavbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { label: "Dashboard", href: "/", icon: "home" },
    { label: "Knowledge Base", href: "/knowledge", icon: "database" },
    { label: "RAG Chat", href: "/chat", icon: "chat" },
    { label: "AI Gateway", href: "/admin/models", icon: "cpu" },
    { label: "Audit & Security", href: "/admin/audit", icon: "shield" },
  ];

  const isItemActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <header className="nav-bar">
      <Link href="/" className="nav-title">
        {/* Authentic Glatt Brand Logo */}
        <img
          src="/glatt-logo.png"
          alt="Glatt Logo"
          className="nav-logo"
        />
        <span className="brand-tag">AI BRAIN</span>
      </Link>

      {/* Mobile Menu Toggle Button */}
      <button
        type="button"
        className="mobile-menu-toggle"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        aria-label="Toggle Navigation Menu"
        aria-expanded={mobileMenuOpen}
      >
        {mobileMenuOpen ? "✕" : "☰"}
      </button>

      {/* Main Nav Menu - completely flat flex without unstyled nested ul/li */}
      <nav className={`nav-menu ${mobileMenuOpen ? "open" : ""}`}>
        {navItems.map((item) => {
          const active = isItemActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-item ${active ? "active" : ""}`}
              aria-current={active ? "page" : undefined}
              onClick={() => setMobileMenuOpen(false)}
            >
              {item.icon === "home" && (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                  <polyline points="9 22 9 12 15 12 15 22"/>
                </svg>
              )}
              {item.icon === "database" && (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <ellipse cx="12" cy="5" rx="9" ry="3"/>
                  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                  <path d="M21 19c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                  <path d="M3 5v14"/>
                  <path d="M21 5v14"/>
                </svg>
              )}
              {item.icon === "chat" && (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
              )}
              {item.icon === "cpu" && (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="4" y="4" width="16" height="16" rx="2" ry="2"/>
                  <rect x="9" y="9" width="6" height="6"/>
                  <line x1="9" y1="1" x2="9" y2="4"/>
                  <line x1="15" y1="1" x2="15" y2="4"/>
                  <line x1="9" y1="20" x2="9" y2="23"/>
                  <line x1="15" y1="20" x2="15" y2="23"/>
                  <line x1="20" y1="9" x2="23" y2="9"/>
                  <line x1="20" y1="15" x2="23" y2="15"/>
                  <line x1="1" y1="9" x2="4" y2="9"/>
                  <line x1="1" y1="15" x2="4" y2="15"/>
                </svg>
              )}
              {item.icon === "shield" && (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
              )}
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Right Side Status & Tenant Pill */}
      <div className="nav-bar-right">
        <div className="tenant-badge">
          <span className="tenant-dot"></span>
          <span>Tenant: Glatt Enterprise</span>
        </div>
      </div>
    </header>
  );
}
