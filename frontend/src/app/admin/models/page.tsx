"use client";

import { useState, useEffect } from "react";
import { fetchWithAuth, ModelStatus } from "@/lib/api";

export default function AdminModelsPage() {
  const [models, setModels] = useState<ModelStatus[]>([]);
  const [loading, setLoading] = useState(true);

  // Reranker Playground state
  const [query, setQuery] = useState("ERR-404 hydraulic calibration");
  const [doc1, setDoc1] = useState("Procedure for calibrating hydraulic pressure sensor ERR-404");
  const [doc2, setDoc2] = useState("Safety rules for office cafeteria");
  const [rerankResults, setRerankResults] = useState<any[]>([]);

  useEffect(() => {
    fetchWithAuth("/models")
      .then((data) => setModels(data))
      .catch((err) => console.error("Failed to load models registry", err))
      .finally(() => setLoading(false));
  }, []);

  const handleTestRerank = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const data = await fetchWithAuth("/models/rerank", {
        method: "POST",
        body: JSON.stringify({
          query,
          documents: [doc1, doc2],
          top_k: 2,
        }),
      });
      setRerankResults(data.results);
    } catch (err: any) {
      alert(`Rerank Test Failed: ${err.message}`);
    }
  };

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0f172a", color: "#f8fafc", padding: "2rem 4rem", fontFamily: "Inter, sans-serif" }}>
      <header style={{ marginBottom: "2.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: "bold", background: "linear-gradient(to right, #38bdf8, #818cf8)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            AI Model Gateway & Health Dashboard
          </h1>
          <p style={{ color: "#64748b", marginTop: "0.25rem" }}>Capability-based provider routing, LLM gateway, Cross-Encoder reranker, and OCR engine status.</p>
        </div>
        <a href="/chat" style={{ color: "#38bdf8", textDecoration: "none", fontSize: "0.9rem" }}>&larr; Back to Chat</a>
      </header>

      {/* Model Capabilities Registry Table */}
      <div style={{ backgroundColor: "#1e293b", padding: "1.75rem", borderRadius: "0.75rem", border: "1px solid #334155", marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.125rem", fontWeight: "600", marginBottom: "1rem" }}>Registered Capabilities & Model Providers</h2>
        {loading ? (
          <div style={{ color: "#94a3b8" }}>Loading model gateway registry...</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #334155", color: "#64748b" }}>
                <th style={{ padding: "0.75rem" }}>Capability</th>
                <th style={{ padding: "0.75rem" }}>Provider Name</th>
                <th style={{ padding: "0.75rem" }}>Active Model</th>
                <th style={{ padding: "0.75rem" }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.capability} style={{ borderBottom: "1px solid #1e293b" }}>
                  <td style={{ padding: "0.75rem", fontWeight: "bold", color: "#38bdf8" }}>{m.capability}</td>
                  <td style={{ padding: "0.75rem" }}>{m.provider_name}</td>
                  <td style={{ padding: "0.75rem", color: "#cbd5e1" }}>{m.model_name}</td>
                  <td style={{ padding: "0.75rem" }}>
                    <span style={{ padding: "0.25rem 0.5rem", borderRadius: "0.25rem", backgroundColor: "#065f46", color: "#34d399", fontSize: "0.75rem" }}>
                      {m.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Reranker Playground */}
      <div style={{ backgroundColor: "#1e293b", padding: "1.75rem", borderRadius: "0.75rem", border: "1px solid #334155" }}>
        <h2 style={{ fontSize: "1.125rem", fontWeight: "600", marginBottom: "1rem" }}>Cross-Encoder Reranker Playground</h2>
        <form onSubmit={handleTestRerank} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", color: "#94a3b8", marginBottom: "0.25rem" }}>Test Query</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ width: "100%", padding: "0.75rem", borderRadius: "0.375rem", backgroundColor: "#0f172a", border: "1px solid #475569", color: "#f8fafc" }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", color: "#94a3b8", marginBottom: "0.25rem" }}>Document 1</label>
            <input
              type="text"
              value={doc1}
              onChange={(e) => setDoc1(e.target.value)}
              style={{ width: "100%", padding: "0.75rem", borderRadius: "0.375rem", backgroundColor: "#0f172a", border: "1px solid #475569", color: "#f8fafc" }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", color: "#94a3b8", marginBottom: "0.25rem" }}>Document 2</label>
            <input
              type="text"
              value={doc2}
              onChange={(e) => setDoc2(e.target.value)}
              style={{ width: "100%", padding: "0.75rem", borderRadius: "0.375rem", backgroundColor: "#0f172a", border: "1px solid #475569", color: "#f8fafc" }}
            />
          </div>
          <button type="submit" style={{ padding: "0.75rem 1.5rem", borderRadius: "0.375rem", backgroundColor: "#2563eb", color: "#fff", fontWeight: "bold", border: "none", alignSelf: "flex-start", cursor: "pointer" }}>
            Execute Rerank Test
          </button>
        </form>

        {rerankResults.length > 0 && (
          <div style={{ marginTop: "1.5rem", borderTop: "1px solid #334155", paddingTop: "1rem" }}>
            <h3 style={{ fontSize: "0.9rem", color: "#38bdf8", marginBottom: "0.5rem" }}>Reranker Score Ranking Output:</h3>
            {rerankResults.map((r, i) => (
              <div key={i} style={{ padding: "0.75rem", borderRadius: "0.375rem", backgroundColor: "#0f172a", marginBottom: "0.5rem", border: "1px solid #334155" }}>
                <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Rank {i + 1} | Score: {(r.score * 100).toFixed(1)}%</div>
                <div style={{ marginTop: "0.25rem", color: "#f8fafc", fontSize: "0.875rem" }}>{r.document_text}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
