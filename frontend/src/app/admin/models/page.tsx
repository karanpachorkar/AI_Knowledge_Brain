"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { fetchWithAuth, ModelStatus } from "@/lib/api";

export default function AdminModelsPage() {
  const [models, setModels] = useState<ModelStatus[]>([]);
  const [loading, setLoading] = useState(true);

  // Reranker Playground state
  const [query, setQuery] = useState("ERR-404 hydraulic calibration");
  const [doc1, setDoc1] = useState("Procedure for calibrating hydraulic pressure sensor ERR-404 on Glatt dryer");
  const [doc2, setDoc2] = useState("General safety guidelines for factory breakrooms");
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
    <>
      <div className="header-banner">
        <div>
          <h1 className="header-title">AI Model Gateway & Health Dashboard</h1>
          <p className="header-subtitle">
            Capability-based provider routing, LLM gateway, Cross-Encoder reranker, and OCR engine status.
          </p>
        </div>
        <Link href="/chat" className="btn btn-secondary btn-sm">
          &larr; Back to RAG Chat
        </Link>
      </div>

      {/* Model Capabilities Registry Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden", marginBottom: "24px" }}>
        <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border-color)" }}>
          <h2 style={{ fontSize: "18px", fontWeight: "600", margin: 0 }}>
            Registered Capabilities & Model Providers
          </h2>
        </div>
        {loading ? (
          <div style={{ padding: "32px", color: "var(--text-secondary)", textAlign: "center" }}>
            Loading model gateway registry...
          </div>
        ) : (
          <div className="table-container" style={{ border: "none", borderRadius: 0, boxShadow: "none" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Capability</th>
                  <th>Provider Name</th>
                  <th>Active Model</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {models.map((m) => (
                  <tr key={m.capability}>
                    <td style={{ fontWeight: "700", color: "var(--color-primary)" }}>{m.capability}</td>
                    <td>{m.provider_name}</td>
                    <td style={{ color: "var(--text-secondary)", fontWeight: "500" }}>{m.model_name}</td>
                    <td>
                      <span className="badge badge-success">
                        {m.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Reranker Playground */}
      <div className="card">
        <div className="card-header">Cross-Encoder Precision Reranker Playground</div>
        <form onSubmit={handleTestRerank} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label required">Test Query</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="form-control"
              required
            />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label required">Candidate Document 1</label>
            <input
              type="text"
              value={doc1}
              onChange={(e) => setDoc1(e.target.value)}
              className="form-control"
              required
            />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label required">Candidate Document 2</label>
            <input
              type="text"
              value={doc2}
              onChange={(e) => setDoc2(e.target.value)}
              className="form-control"
              required
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary"
            style={{ alignSelf: "flex-start", marginTop: "8px" }}
          >
            Execute Rerank Test
          </button>
        </form>

        {rerankResults.length > 0 && (
          <div style={{ marginTop: "24px", borderTop: "1px solid var(--border-color)", paddingTop: "16px" }}>
            <h3 style={{ fontSize: "16px", color: "var(--color-primary)", fontWeight: "700", marginBottom: "12px" }}>
              Reranker Score Ranking Output:
            </h3>
            {rerankResults.map((r, i) => (
              <div
                key={i}
                style={{
                  padding: "16px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--bg-secondary)",
                  marginBottom: "12px",
                  border: "1px solid var(--border-color)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-primary)" }}>Rank {i + 1}</span>
                  <span className="badge badge-success">Confidence: {(r.score * 100).toFixed(1)}%</span>
                </div>
                <div style={{ marginTop: "4px", color: "var(--text-secondary)", fontSize: "14px" }}>
                  {r.document_text}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
