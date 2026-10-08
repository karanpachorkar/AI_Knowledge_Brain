"use client";

import { useState } from "react";
import { fetchWithAuth } from "@/lib/api";

export default function KnowledgeBasePage() {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [uploading, setUploading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title || uploading) return;

    setUploading(true);
    setStatusMsg("Uploading and processing file...");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title);
      formData.append("workspace_id", "00000000-0000-0000-0000-000000000001");
      formData.append("knowledge_base_id", "00000000-0000-0000-0000-000000000002");

      await fetchWithAuth("/documents/upload", {
        method: "POST",
        body: formData,
      });

      setStatusMsg("Document ingested and indexed successfully!");
      setTitle("");
      setFile(null);
    } catch (err: any) {
      setStatusMsg(`Upload Error: ${err.message || "Failed to upload document"}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0f172a", color: "#f8fafc", padding: "2rem 4rem", fontFamily: "Inter, sans-serif" }}>
      <header style={{ marginBottom: "2.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: "bold", background: "linear-gradient(to right, #38bdf8, #818cf8)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Knowledge Base Manager
          </h1>
          <p style={{ color: "#64748b", marginTop: "0.25rem" }}>Upload documents, configure generic document types, and index into Qdrant & OpenSearch engines.</p>
        </div>
        <a href="/chat" style={{ color: "#38bdf8", textDecoration: "none", fontSize: "0.9rem" }}>&larr; Back to RAG Chat</a>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "2rem" }}>
        {/* Document Ingestion Form */}
        <div style={{ backgroundColor: "#1e293b", padding: "1.75rem", borderRadius: "0.75rem", border: "1px solid #334155" }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: "600", marginBottom: "1.25rem" }}>Ingest New Document</h2>
          <form onSubmit={handleUpload} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.85rem", color: "#94a3b8", marginBottom: "0.5rem" }}>Document Title</label>
              <input
                type="text"
                placeholder="e.g. Hydraulic Pump Maintenance SOP"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                style={{ width: "100%", padding: "0.75rem", borderRadius: "0.375rem", backgroundColor: "#0f172a", border: "1px solid #475569", color: "#f8fafc" }}
                required
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.85rem", color: "#94a3b8", marginBottom: "0.5rem" }}>Select Binary File (.pdf, .docx, .txt, .md)</label>
              <input
                type="file"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "0.375rem", backgroundColor: "#0f172a", border: "1px solid #475569", color: "#94a3b8" }}
                required
              />
            </div>

            <button
              type="submit"
              disabled={uploading}
              style={{
                padding: "0.875rem",
                borderRadius: "0.375rem",
                backgroundColor: "#2563eb",
                color: "#ffffff",
                fontWeight: "600",
                border: "none",
                cursor: uploading ? "not-allowed" : "pointer",
                marginTop: "0.5rem",
              }}
            >
              {uploading ? "Ingesting..." : "Upload & Parse Document"}
            </button>

            {statusMsg && (
              <div style={{ fontSize: "0.85rem", color: statusMsg.includes("Error") ? "#ef4444" : "#10b981" }}>
                {statusMsg}
              </div>
            )}
          </form>
        </div>

        {/* Knowledge Base Overview */}
        <div style={{ backgroundColor: "#1e293b", padding: "1.75rem", borderRadius: "0.75rem", border: "1px solid #334155" }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: "600", marginBottom: "1rem" }}>Indexed Documents & Chunks</h2>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem", textAlign: "left" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #334155", color: "#64748b" }}>
                  <th style={{ padding: "0.75rem" }}>Title</th>
                  <th style={{ padding: "0.75rem" }}>Knowledge Base</th>
                  <th style={{ padding: "0.75rem" }}>Status</th>
                  <th style={{ padding: "0.75rem" }}>Indexed Chunks</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: "1px solid #1e293b" }}>
                  <td style={{ padding: "0.75rem", fontWeight: "500" }}>Hydraulic Maintenance Manual</td>
                  <td style={{ padding: "0.75rem", color: "#94a3b8" }}>Default KB</td>
                  <td style={{ padding: "0.75rem" }}>
                    <span style={{ padding: "0.25rem 0.5rem", borderRadius: "0.25rem", backgroundColor: "#065f46", color: "#34d399", fontSize: "0.75rem" }}>READY</span>
                  </td>
                  <td style={{ padding: "0.75rem", color: "#38bdf8" }}>1 chunks</td>
                </tr>
                <tr>
                  <td style={{ padding: "0.75rem", fontWeight: "500" }}>Calibration Guide SOP</td>
                  <td style={{ padding: "0.75rem", color: "#94a3b8" }}>Default KB</td>
                  <td style={{ padding: "0.75rem" }}>
                    <span style={{ padding: "0.25rem 0.5rem", borderRadius: "0.25rem", backgroundColor: "#065f46", color: "#34d399", fontSize: "0.75rem" }}>READY</span>
                  </td>
                  <td style={{ padding: "0.75rem", color: "#38bdf8" }}>1 chunks</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
