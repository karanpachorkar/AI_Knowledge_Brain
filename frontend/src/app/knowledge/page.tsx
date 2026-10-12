"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchWithAuth } from "@/lib/api";

interface DocumentVersion {
  id: string;
  version_number: number;
  file_name: string;
  status: string;
  metadata_json?: {
    generated_chunks?: number;
    error_message?: string;
  };
}

interface DocumentItem {
  id: string;
  title: string;
  versions: DocumentVersion[];
}

export default function KnowledgeBasePage() {
  const [activeTab, setActiveTab] = useState<"documents" | "search" | "health">("documents");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [uploading, setUploading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  
  // Search playground state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  const kbId = "00000000-0000-0000-0000-000000000002";

  const loadDocuments = async () => {
    try {
      const res = await fetchWithAuth(`/documents/kb/${kbId}`);
      if (Array.isArray(res)) {
        setDocuments(res);
      }
    } catch {
      // Fallback empty list if unauthenticated or error
    }
  };

  useEffect(() => {
    loadDocuments();
    const interval = setInterval(loadDocuments, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title || uploading) return;

    setUploading(true);
    setStatusMsg("Uploading document to MinIO and enqueuing Celery worker pipeline...");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title);
      formData.append("workspace_id", "00000000-0000-0000-0000-000000000001");
      formData.append("knowledge_base_id", kbId);

      await fetchWithAuth("/documents/upload", {
        method: "POST",
        body: formData,
      });

      setStatusMsg("Document uploaded & processing job queued successfully!");
      setTitle("");
      setFile(null);
      await loadDocuments();
    } catch (err: any) {
      setStatusMsg(`Upload Error: ${err.message || "Failed to upload document"}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      await fetchWithAuth(`/documents/${docId}`, { method: "DELETE" });
      setStatusMsg("Document and all derived vectors & indexes deleted successfully.");
      await loadDocuments();
    } catch (err: any) {
      setStatusMsg(`Delete Error: ${err.message || "Failed to delete document"}`);
    }
  };

  const handleRetry = async (docId: string) => {
    try {
      await fetchWithAuth(`/documents/${docId}/retry`, { method: "POST" });
      setStatusMsg("Processing retried for document.");
      await loadDocuments();
    } catch (err: any) {
      setStatusMsg(`Retry Error: ${err.message || "Failed to retry document"}`);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || searching) return;
    setSearching(true);
    try {
      // Test search using chat endpoint retrieval preview
      const res = await fetchWithAuth("/chat", {
        method: "POST",
        body: JSON.stringify({
          workspace_id: "00000000-0000-0000-0000-000000000001",
          message: searchQuery,
          strict_grounding: false,
        }),
      });
      setSearchResults(res.citations || []);
    } catch (err: any) {
      alert(`Search error: ${err.message}`);
    } finally {
      setSearching(false);
    }
  };

  const renderStatusBadge = (status: string) => {
    const s = status ? status.toUpperCase() : "QUEUED";
    if (s === "READY") {
      return <span className="badge badge-success">READY</span>;
    } else if (s === "FAILED") {
      return <span className="badge badge-danger">FAILED</span>;
    } else if (["PROCESSING", "OCR", "CHUNKING", "EMBEDDING", "INDEXING"].includes(s)) {
      return <span className="badge badge-warning">{s}</span>;
    }
    return <span className="badge badge-primary">{s}</span>;
  };

  const totalChunks = documents.reduce((acc, doc) => {
    const latest = doc.versions && doc.versions.length > 0 ? doc.versions[doc.versions.length - 1] : null;
    return acc + (latest?.metadata_json?.generated_chunks || 0);
  }, 0);

  return (
    <>
      <div className="header-banner">
        <div>
          <h1 className="header-title">Knowledge Base Manager</h1>
          <p className="header-subtitle">
            Upload Glatt technical documents, monitor async Celery worker pipeline, and manage Qdrant vectors & OpenSearch BM25 indexes.
          </p>
        </div>
        <Link href="/chat" className="btn btn-secondary btn-sm">
          &larr; Back to RAG Chat
        </Link>
      </div>

      {/* Interactive Sub-Tabs Bar */}
      <div className="subtab-header">
        <button
          className={`subtab-button ${activeTab === "documents" ? "active" : ""}`}
          onClick={() => setActiveTab("documents")}
        >
          📑 Ingestion & Document List ({documents.length})
        </button>
        <button
          className={`subtab-button ${activeTab === "search" ? "active" : ""}`}
          onClick={() => setActiveTab("search")}
        >
          🔍 Hybrid Search & Chunk Inspector
        </button>
        <button
          className={`subtab-button ${activeTab === "health" ? "active" : ""}`}
          onClick={() => setActiveTab("health")}
        >
          ⚡ Storage & Vector Index Metrics
        </button>
      </div>

      {/* Tab 1: Documents & Ingestion */}
      {activeTab === "documents" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "24px" }}>
          {/* Document Ingestion Form */}
          <div className="card">
            <div className="card-header">Ingest Technical Document</div>
            <form onSubmit={handleUpload} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label required">Document Title</label>
                <input
                  type="text"
                  placeholder="e.g. Glatt WSG 120 Fluid Bed Dryer SOP"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="form-control"
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label required">Select Binary File (.pdf, .docx, .txt, .md)</label>
                <input
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="form-control"
                  style={{ padding: "8px 12px" }}
                  required
                />
                <span className="form-help">Supported formats: PDF, DOCX, Markdown, Text. Automatic OCR enabled.</span>
              </div>

              <button
                type="submit"
                disabled={uploading}
                className="btn btn-primary"
                style={{ marginTop: "8px" }}
              >
                {uploading ? "Uploading & Enqueuing..." : "Upload Document"}
              </button>

              {statusMsg && (
                <div
                  style={{
                    fontSize: "13px",
                    fontWeight: "500",
                    padding: "10px 14px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: statusMsg.includes("Error") ? "var(--bg-secondary)" : "rgba(16, 185, 129, 0.1)",
                    color: statusMsg.includes("Error") ? "var(--color-danger)" : "var(--color-success-dark)",
                    border: `1px solid ${statusMsg.includes("Error") ? "var(--color-danger)" : "var(--color-success)"}`,
                  }}
                >
                  {statusMsg}
                </div>
              )}
            </form>
          </div>

          {/* Knowledge Base Overview */}
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border-color)" }}>
              <h2 style={{ fontSize: "18px", fontWeight: "600", margin: 0 }}>
                Indexed Documents & Worker Status
              </h2>
            </div>
            <div className="table-container" style={{ border: "none", borderRadius: 0, boxShadow: "none" }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Chunks</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.length === 0 ? (
                    <tr>
                      <td colSpan={4} style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)" }}>
                        No documents ingested yet. Upload an SOP or manual to begin.
                      </td>
                    </tr>
                  ) : (
                    documents.map((doc) => {
                      const latestVersion = doc.versions && doc.versions.length > 0 ? doc.versions[doc.versions.length - 1] : null;
                      const status = latestVersion ? latestVersion.status : "QUEUED";
                      const chunksCount = latestVersion?.metadata_json?.generated_chunks ?? 0;

                      return (
                        <tr key={doc.id}>
                          <td style={{ fontWeight: "600" }}>{doc.title}</td>
                          <td>{renderStatusBadge(status)}</td>
                          <td style={{ color: "var(--color-primary)", fontWeight: "600" }}>{chunksCount} chunks</td>
                          <td>
                            <div style={{ display: "flex", gap: "8px" }}>
                              {status === "FAILED" && (
                                <button
                                  onClick={() => handleRetry(doc.id)}
                                  className="btn btn-secondary btn-sm"
                                  style={{ color: "var(--color-warning)" }}
                                >
                                  Retry
                                </button>
                              )}
                              <button
                                onClick={() => handleDelete(doc.id)}
                                className="btn btn-danger btn-sm"
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Hybrid Search & Chunk Inspector */}
      {activeTab === "search" && (
        <div className="card">
          <div className="card-header">Hybrid Dense (Qdrant) + Sparse (OpenSearch) Search Preview</div>
          <form onSubmit={handleSearch} style={{ display: "flex", gap: "12px", marginBottom: "24px" }}>
            <input
              type="text"
              placeholder="Search across indexed documents (e.g. calibration pressure threshold, nozzle spray rate)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="form-control"
              style={{ flex: 1 }}
            />
            <button
              type="submit"
              disabled={searching}
              className="btn btn-primary"
            >
              {searching ? "Searching..." : "Execute Search"}
            </button>
          </form>

          {searchResults.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <h3 style={{ fontSize: "16px", color: "var(--color-primary)", fontWeight: "700" }}>
                Retrieved Chunks & Relevance Ranking
              </h3>
              {searchResults.map((citation, i) => (
                <div
                  key={citation.chunk_id || i}
                  style={{
                    padding: "16px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "var(--bg-secondary)",
                    border: "1px solid var(--border-color)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                    <span style={{ fontWeight: "700", color: "var(--text-primary)" }}>
                      {citation.document_title || "Indexed Document"}
                    </span>
                    <span className="badge badge-success">
                      Score: {(citation.relevance_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: "1.5", margin: 0 }}>
                    {citation.snippet}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: "var(--text-muted)", padding: "32px 0", textAlign: "center" }}>
              Enter a technical term or part number to inspect retrieved vector + keyword chunks.
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Storage & Vector Metrics */}
      {activeTab === "health" && (
        <div className="grid-metrics">
          <div className="card-metric">
            <div className="card-header-icon">
              <span className="metric-label">Total Documents</span>
              <div className="icon-wrapper icon-red">📑</div>
            </div>
            <div className="metric-value">{documents.length} Files</div>
            <span className="module-tag">PostgreSQL 16 Relational Store</span>
          </div>

          <div className="card-metric">
            <div className="card-header-icon">
              <span className="metric-label">Dense Vector Embeddings</span>
              <div className="icon-wrapper icon-purple">⚡</div>
            </div>
            <div className="metric-value">{totalChunks} Embeddings</div>
            <span className="module-tag">Qdrant Vector Engine</span>
          </div>

          <div className="card-metric">
            <div className="card-header-icon">
              <span className="metric-label">BM25 Sparse Index</span>
              <div className="icon-wrapper icon-emerald">🔍</div>
            </div>
            <div className="metric-value">OpenSearch Active</div>
            <span className="module-tag">Keyword & Exact Match</span>
          </div>
        </div>
      )}
    </>
  );
}
