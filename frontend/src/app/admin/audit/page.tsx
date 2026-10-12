"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
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
    <>
      <div className="header-banner">
        <div>
          <h1 className="header-title">Security & Compliance Audit Logs</h1>
          <p className="header-subtitle">
            Tenant-isolated security audit log timeline with IP tracking and user correlation for 21 CFR Part 11 compliance.
          </p>
        </div>
        <Link href="/chat" className="btn btn-secondary btn-sm">
          &larr; Back to RAG Chat
        </Link>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border-color)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ fontSize: "18px", fontWeight: "600", margin: 0 }}>
            Audit Log Event Stream
          </h2>
          <span className="badge badge-primary">
            {logs.length} Recorded Events
          </span>
        </div>
        {loading ? (
          <div style={{ padding: "32px", color: "var(--text-secondary)", textAlign: "center" }}>
            Loading tenant audit trail...
          </div>
        ) : logs.length === 0 ? (
          <div style={{ color: "var(--text-muted)", padding: "48px 0", textAlign: "center" }}>
            No audit log events recorded yet.
          </div>
        ) : (
          <div className="table-container" style={{ border: "none", borderRadius: 0, boxShadow: "none" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>Resource Type</th>
                  <th>Resource ID</th>
                  <th>IP Address</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td>
                      <span className="badge badge-primary" style={{ fontWeight: "700" }}>
                        {log.action}
                      </span>
                    </td>
                    <td style={{ fontWeight: "600", color: "var(--text-primary)" }}>
                      {log.resource_type}
                    </td>
                    <td style={{ color: "var(--text-secondary)", fontFamily: "monospace", fontSize: "13px" }}>
                      {log.resource_id || "N/A"}
                    </td>
                    <td style={{ color: "var(--text-muted)", fontFamily: "monospace", fontSize: "13px" }}>
                      {log.ip_address || "127.0.0.1"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
