"use client";

import { useEffect, useRef, useState } from "react";
import { fetchWithAuth } from "@/lib/api";

interface Chunk {
  chunk_id: string;
  chunk_index: number;
  section_title: string | null;
  page_number: number | null;
  content: string;
  metadata: {
    document_title?: string;
    chunk_size?: number;
    is_table?: boolean;
  };
}

interface DocumentViewerProps {
  docId: string;
  docTitle: string;
  docMimeType?: string;
  onClose: () => void;
}

export default function DocumentViewer({
  docId,
  docTitle,
  docMimeType,
  onClose,
}: DocumentViewerProps) {
  const [activeTab, setActiveTab] = useState<"raw" | "chunks">("raw");
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(true);
  const [fileError, setFileError] = useState<string | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [chunksError, setChunksError] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState("");
  const [expandedChunk, setExpandedChunk] = useState<string | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  const isPDF = docMimeType === "application/pdf" || docTitle.toLowerCase().endsWith(".pdf");
  const isText = docMimeType?.startsWith("text/") || docTitle.toLowerCase().endsWith(".txt") || docTitle.toLowerCase().endsWith(".md");

  // Load raw file
  useEffect(() => {
    const loadFile = async () => {
      setFileLoading(true);
      setFileError(null);
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
        const res = await fetch(`/api/v1/documents/${docId}/file`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        objectUrlRef.current = url;
        setFileUrl(url);
      } catch (err: any) {
        setFileError(err.message || "Failed to load file.");
      } finally {
        setFileLoading(false);
      }
    };
    loadFile();
    return () => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    };
  }, [docId]);

  // Load chunks on tab switch
  useEffect(() => {
    if (activeTab !== "chunks" || chunks.length > 0) return;
    const loadChunks = async () => {
      setChunksLoading(true);
      setChunksError(null);
      try {
        const data = await fetchWithAuth(`/documents/${docId}/chunks`);
        setChunks(Array.isArray(data) ? data : []);
      } catch (err: any) {
        setChunksError(err.message || "Failed to load chunks.");
      } finally {
        setChunksLoading(false);
      }
    };
    loadChunks();
  }, [activeTab, docId, chunks.length]);

  const filteredChunks = chunks.filter((c) => {
    if (!searchFilter.trim()) return true;
    const q = searchFilter.toLowerCase();
    return (
      c.content.toLowerCase().includes(q) ||
      (c.section_title?.toLowerCase().includes(q) ?? false)
    );
  });

  // Handle backdrop click
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      onClick={handleBackdropClick}
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.55)",
        backdropFilter: "blur(4px)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
      }}
    >
      <div
        style={{
          background: "var(--bg-primary)",
          borderRadius: "var(--radius-xl)",
          boxShadow: "var(--shadow-2xl)",
          width: "100%",
          maxWidth: "1100px",
          height: "88vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          border: "1px solid var(--border-color)",
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "16px 24px",
            borderBottom: "1px solid var(--border-color)",
            flexShrink: 0,
            background: "var(--bg-primary)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "var(--radius-md)",
                background: "rgba(196,30,58,0.1)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                fontSize: "18px",
              }}
            >
              📄
            </div>
            <div style={{ minWidth: 0 }}>
              <div
                style={{
                  fontWeight: "var(--font-semibold)",
                  fontSize: "var(--font-md)",
                  color: "var(--text-primary)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {docTitle}
              </div>
              <div style={{ fontSize: "var(--font-xs)", color: "var(--text-muted)", marginTop: "2px" }}>
                {chunks.length > 0 ? `${chunks.length} indexed chunks` : docMimeType || "Document"}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
            {fileUrl && (
              <a
                href={fileUrl}
                download={docTitle}
                className="btn btn-secondary btn-sm"
                title="Download original file"
              >
                ⬇ Download
              </a>
            )}
            <button
              onClick={onClose}
              style={{
                background: "none",
                border: "1px solid var(--border-color)",
                borderRadius: "var(--radius-md)",
                width: "34px",
                height: "34px",
                cursor: "pointer",
                fontSize: "18px",
                color: "var(--text-secondary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all var(--transition-fast)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = "var(--bg-secondary)";
                (e.currentTarget as HTMLButtonElement).style.color = "var(--text-primary)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = "none";
                (e.currentTarget as HTMLButtonElement).style.color = "var(--text-secondary)";
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Tab Bar */}
        <div
          style={{
            display: "flex",
            borderBottom: "2px solid var(--border-color)",
            padding: "0 24px",
            gap: "4px",
            flexShrink: 0,
            background: "var(--bg-primary)",
          }}
        >
          {(
            [
              { key: "raw", label: "📄 Raw File Viewer", desc: isPDF ? "PDF" : isText ? "Text" : "Binary" },
              { key: "chunks", label: `🧩 Chunk Inspector`, desc: chunks.length > 0 ? `${chunks.length} chunks` : "Indexed" },
            ] as const
          ).map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                background: "none",
                border: "none",
                borderBottom:
                  activeTab === tab.key
                    ? "2px solid var(--color-primary)"
                    : "2px solid transparent",
                marginBottom: "-2px",
                padding: "12px 16px",
                cursor: "pointer",
                color:
                  activeTab === tab.key ? "var(--color-primary)" : "var(--text-secondary)",
                fontWeight: activeTab === tab.key ? "var(--font-semibold)" : "var(--font-normal)",
                fontSize: "var(--font-sm)",
                transition: "all var(--transition-fast)",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              {tab.label}
              <span
                style={{
                  fontSize: "11px",
                  padding: "1px 6px",
                  borderRadius: "var(--radius-full)",
                  background:
                    activeTab === tab.key
                      ? "rgba(196,30,58,0.1)"
                      : "var(--bg-secondary)",
                  color:
                    activeTab === tab.key ? "var(--color-primary)" : "var(--text-muted)",
                  fontWeight: "600",
                }}
              >
                {tab.desc}
              </span>
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
          {/* ── RAW FILE TAB ── */}
          {activeTab === "raw" && (
            <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
              {fileLoading && (
                <div
                  style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexDirection: "column",
                    gap: "16px",
                    color: "var(--text-muted)",
                  }}
                >
                  <div
                    style={{
                      width: "40px",
                      height: "40px",
                      border: "3px solid var(--border-color)",
                      borderTopColor: "var(--color-primary)",
                      borderRadius: "50%",
                      animation: "spin 0.8s linear infinite",
                    }}
                  />
                  <span style={{ fontSize: "var(--font-sm)" }}>Loading document binary from storage...</span>
                </div>
              )}

              {fileError && !fileLoading && (
                <div
                  style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexDirection: "column",
                    gap: "12px",
                    padding: "32px",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "48px" }}>⚠️</div>
                  <div style={{ fontWeight: "600", color: "var(--text-primary)" }}>
                    File Not Available
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "var(--font-sm)", maxWidth: "400px" }}>
                    {fileError}. The file may still be processing, or storage is unavailable.
                  </div>
                </div>
              )}

              {fileUrl && !fileLoading && !fileError && isPDF && (
                <iframe
                  src={fileUrl}
                  style={{
                    width: "100%",
                    height: "100%",
                    border: "none",
                    background: "#f0f0f0",
                  }}
                  title={docTitle}
                />
              )}

              {fileUrl && !fileLoading && !fileError && isText && (
                <TextViewer url={fileUrl} />
              )}

              {fileUrl && !fileLoading && !fileError && !isPDF && !isText && (
                <div
                  style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexDirection: "column",
                    gap: "16px",
                    padding: "32px",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: "64px" }}>📎</div>
                  <div style={{ fontWeight: "600", fontSize: "var(--font-lg)", color: "var(--text-primary)" }}>
                    {docTitle}
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "var(--font-sm)" }}>
                    This file type ({docMimeType}) cannot be previewed inline.
                  </div>
                  <a href={fileUrl} download={docTitle} className="btn btn-primary">
                    ⬇ Download File
                  </a>
                </div>
              )}
            </div>
          )}

          {/* ── CHUNKS TAB ── */}
          {activeTab === "chunks" && (
            <div
              style={{
                height: "100%",
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
              }}
            >
              {/* Chunks Toolbar */}
              <div
                style={{
                  padding: "12px 24px",
                  borderBottom: "1px solid var(--border-color)",
                  flexShrink: 0,
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  background: "var(--bg-secondary)",
                }}
              >
                <input
                  type="text"
                  placeholder="Filter chunks by keyword or section title..."
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  className="form-control"
                  style={{ flex: 1, fontSize: "var(--font-sm)" }}
                />
                {chunks.length > 0 && (
                  <span
                    style={{
                      fontSize: "var(--font-xs)",
                      color: "var(--text-muted)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {filteredChunks.length} / {chunks.length} chunks
                  </span>
                )}
              </div>

              {/* Chunks List */}
              <div style={{ flex: 1, overflowY: "auto", padding: "16px 24px" }}>
                {chunksLoading && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "12px",
                      padding: "48px",
                      color: "var(--text-muted)",
                    }}
                  >
                    <div
                      style={{
                        width: "32px",
                        height: "32px",
                        border: "3px solid var(--border-color)",
                        borderTopColor: "var(--color-primary)",
                        borderRadius: "50%",
                        animation: "spin 0.8s linear infinite",
                      }}
                    />
                    Loading chunks from Qdrant vector store...
                  </div>
                )}

                {chunksError && !chunksLoading && (
                  <div
                    style={{
                      padding: "32px",
                      textAlign: "center",
                      color: "var(--color-danger)",
                      fontSize: "var(--font-sm)",
                    }}
                  >
                    ⚠️ {chunksError}
                  </div>
                )}

                {!chunksLoading && !chunksError && filteredChunks.length === 0 && (
                  <div
                    style={{
                      padding: "48px",
                      textAlign: "center",
                      color: "var(--text-muted)",
                      fontSize: "var(--font-sm)",
                    }}
                  >
                    {chunks.length === 0
                      ? "No chunks found. The document may still be processing or failed indexing."
                      : "No chunks match your filter."}
                  </div>
                )}

                {!chunksLoading &&
                  !chunksError &&
                  filteredChunks.map((chunk) => {
                    const isExpanded = expandedChunk === chunk.chunk_id;
                    const preview = chunk.content.slice(0, 280);
                    const hasMore = chunk.content.length > 280;

                    return (
                      <div
                        key={chunk.chunk_id}
                        style={{
                          border: "1px solid var(--border-color)",
                          borderRadius: "var(--radius-md)",
                          marginBottom: "10px",
                          background: "var(--bg-primary)",
                          overflow: "hidden",
                          transition: "box-shadow var(--transition-fast)",
                          boxShadow: isExpanded ? "var(--shadow-md)" : "var(--shadow-xs)",
                        }}
                      >
                        {/* Chunk Header */}
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "10px 16px",
                            background: isExpanded ? "rgba(196,30,58,0.04)" : "var(--bg-secondary)",
                            borderBottom: isExpanded ? "1px solid var(--border-color)" : "none",
                            cursor: "pointer",
                            userSelect: "none",
                          }}
                          onClick={() =>
                            setExpandedChunk(isExpanded ? null : chunk.chunk_id)
                          }
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                justifyContent: "center",
                                width: "26px",
                                height: "26px",
                                borderRadius: "var(--radius-sm)",
                                background: "rgba(196,30,58,0.1)",
                                color: "var(--color-primary)",
                                fontSize: "11px",
                                fontWeight: "700",
                                flexShrink: 0,
                              }}
                            >
                              #{chunk.chunk_index + 1}
                            </span>
                            <div>
                              <span
                                style={{
                                  fontWeight: "600",
                                  fontSize: "var(--font-sm)",
                                  color: "var(--text-primary)",
                                }}
                              >
                                {chunk.section_title || "Untitled Section"}
                              </span>
                              {chunk.page_number != null && (
                                <span
                                  style={{
                                    fontSize: "var(--font-xs)",
                                    color: "var(--text-muted)",
                                    marginLeft: "8px",
                                  }}
                                >
                                  Page {chunk.page_number}
                                </span>
                              )}
                            </div>
                          </div>

                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            {chunk.metadata?.is_table && (
                              <span
                                style={{
                                  fontSize: "11px",
                                  fontWeight: "700",
                                  padding: "2px 8px",
                                  borderRadius: "var(--radius-full)",
                                  background: "rgba(59,130,246,0.1)",
                                  color: "var(--color-info)",
                                }}
                              >
                                TABLE
                              </span>
                            )}
                            <span
                              style={{
                                fontSize: "11px",
                                color: "var(--text-muted)",
                              }}
                            >
                              {chunk.metadata?.chunk_size
                                ? `${chunk.metadata.chunk_size} chars`
                                : ""}
                            </span>
                            <span
                              style={{
                                fontSize: "16px",
                                color: "var(--text-muted)",
                                transition: "transform 0.2s",
                                transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
                              }}
                            >
                              ▾
                            </span>
                          </div>
                        </div>

                        {/* Chunk Content */}
                        <div style={{ padding: "14px 16px" }}>
                          <pre
                            style={{
                              fontFamily: "'SF Mono', 'Fira Code', 'Courier New', monospace",
                              fontSize: "12.5px",
                              lineHeight: "1.7",
                              color: "var(--text-primary)",
                              whiteSpace: "pre-wrap",
                              wordBreak: "break-word",
                              margin: 0,
                            }}
                          >
                            {isExpanded ? chunk.content : preview}
                            {!isExpanded && hasMore && (
                              <span style={{ color: "var(--text-muted)" }}>…</span>
                            )}
                          </pre>
                          {hasMore && (
                            <button
                              onClick={() =>
                                setExpandedChunk(isExpanded ? null : chunk.chunk_id)
                              }
                              style={{
                                marginTop: "8px",
                                background: "none",
                                border: "none",
                                color: "var(--color-primary)",
                                cursor: "pointer",
                                fontSize: "var(--font-xs)",
                                fontWeight: "600",
                                padding: 0,
                              }}
                            >
                              {isExpanded ? "Show less ▲" : `Show full chunk (${chunk.content.length} chars) ▼`}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

// ── Text file viewer sub-component ──
function TextViewer({ url }: { url: string }) {
  const [text, setText] = useState<string | null>(null);

  useEffect(() => {
    fetch(url)
      .then((r) => r.text())
      .then(setText)
      .catch(() => setText("Failed to load text content."));
  }, [url]);

  return (
    <div
      style={{
        flex: 1,
        overflow: "auto",
        padding: "24px 32px",
        background: "#fafafa",
      }}
    >
      <pre
        style={{
          fontFamily: "'SF Mono', 'Fira Code', 'Courier New', monospace",
          fontSize: "13px",
          lineHeight: "1.8",
          color: "var(--text-primary)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          margin: 0,
        }}
      >
        {text ?? "Loading..."}
      </pre>
    </div>
  );
}
