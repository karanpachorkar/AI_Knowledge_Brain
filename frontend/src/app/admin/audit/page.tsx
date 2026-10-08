"use client";

import { useState, useEffect } from "react";
import { AuditLog, fetchWithAuth } from "@/lib/api";

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWithAuth("/audit-logs")
      .then((data) => setLogs(data))
      .catch((err) => console.error("Failed to load audit logs", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0f172a", color: "#f8fafc", padding: "2rem 4rem", fontFamily: "Inter, sans-serif" }}>
      <header style={{ marginBottom: "2.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: "bold", background: "linear-gradient(to right, #38bdf8, #818cf8)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Security & Compliance Audit Logs
          </h1>
          <p style={{ color: "#64748b", marginTop: "0.25rem" }}>Tenant-isolated security audit log timeline with IP tracking and user correlation.</p>
        </div>
        <a href="/chat" style={{ color: "#38bdf8", textDecoration: "none", fontSize: "0.9rem" }}>&larr; Back to Chat</a>
      </header>

      <div style={{ backgroundColor: "#1e293b", padding: "1.75rem", borderRadius: "0.75rem", border: "1px solid #334155" }}>
        <h2 style={{ fontSize: "1.125rem", fontWeight: "600", marginBottom: "1rem" }}>Audit Log Event Stream</h2>
        {loading ? (
          <div style={{ color: "#94a3b8" }}>Loading tenant audit trail...</div>
        ) : logs.length === 0 ? (
          <div style={{ color: "#64748b", padding: "2rem 0", textAlign: "center" }}>No audit log events recorded yet.</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #334155", color: "#64748b" }}>
                <th style={{ padding: "0.75rem" }}>Timestamp</th>
                <th style={{ padding: "0.75rem" }}>Action</th>
                <th style={{ padding: "0.75rem" }}>Resource</th>
                <th style={{ padding: "0.75rem" }}>Resource ID</th>
                <th style={{ padding: "0.75rem" }}>IP Address</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} style={{ borderBottom: "1px solid #1e293b" }}>
                  <td style={{ padding: "0.75rem", color: "#94a3b8" }}>{new Date(log.created_at).toLocaleString()}</td>
                  <td style={{ padding: "0.75rem", fontWeight: "bold", color: "#38bdf8" }}>{log.action}</td>
                  <td style={{ padding: "0.75rem" }}>{log.resource_type}</td>
                  <td style={{ padding: "0.75rem", color: "#cbd5e1" }}>{log.resource_id || "N/A"}</td>
                  <td style={{ padding: "0.75rem", color: "#64748b" }}>{log.ip_address || "127.0.0.1"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
