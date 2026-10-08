"use client";

import { useState, useEffect } from "react";
import { Citation, fetchWithAuth } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  is_grounded?: boolean;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [strictGrounding, setStrictGrounding] = useState(true);
  const [loading, setLoading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // Mock workspace id or fetch active workspace
      const workspaceId = "00000000-0000-0000-0000-000000000001";
      const data = await fetchWithAuth("/chat", {
        method: "POST",
        body: JSON.stringify({
          workspace_id: workspaceId,
          message: userMessage.content,
          strict_grounding: strictGrounding,
        }),
      });

      const assistantMessage: Message = {
        id: data.message_id,
        role: "assistant",
        content: data.answer,
        citations: data.citations,
        is_grounded: data.is_grounded,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const errorMsg: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: `Error: ${err.message || "Failed to reach RAG chat backend."}`,
        is_grounded: false,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", backgroundColor: "#0f172a", color: "#f8fafc", fontFamily: "Inter, sans-serif" }}>
      {/* Sidebar */}
      <div style={{ width: "280px", borderRight: "1px solid #334155", padding: "1.5rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
        <h2 style={{ fontSize: "1.25rem", fontWeight: "bold", background: "linear-gradient(to right, #38bdf8, #818cf8)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          Enterprise AI Brain
        </h2>
        <div style={{ fontSize: "0.875rem", color: "#94a3b8" }}>RAG Chat Workspace</div>

        <div style={{ marginTop: "1rem", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.85rem", color: "#cbd5e1" }}>Strict Grounding</span>
          <input
            type="checkbox"
            checked={strictGrounding}
            onChange={(e) => setStrictGrounding(e.target.checked)}
            style={{ width: "18px", height: "18px", cursor: "pointer" }}
          />
        </div>

        <div style={{ flex: 1, marginTop: "1.5rem", borderTop: "1px solid #1e293b", paddingTop: "1rem" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: "600", textTransform: "uppercase", color: "#64748b", marginBottom: "0.5rem" }}>Conversations</div>
          <div style={{ padding: "0.5rem 0.75rem", borderRadius: "0.375rem", backgroundColor: "#1e293b", fontSize: "0.875rem", color: "#38bdf8" }}>
            Current RAG Session
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <header style={{ padding: "1.25rem 2rem", borderBottom: "1px solid #334155", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1 style={{ fontSize: "1.125rem", fontWeight: "600" }}>Knowledge Assistant</h1>
            <p style={{ fontSize: "0.85rem", color: "#64748b" }}>Permission-aware grounded synthesis with source inline citations</p>
          </div>
          <a href="/knowledge" style={{ color: "#38bdf8", textDecoration: "none", fontSize: "0.875rem" }}>Manage Knowledge Base &rarr;</a>
        </header>

        {/* Message Stream */}
        <div style={{ flex: 1, overflowY: "auto", padding: "2rem", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {messages.length === 0 && (
            <div style={{ margin: "auto", textAlign: "center", color: "#64748b" }}>
              <h3 style={{ fontSize: "1.25rem", color: "#cbd5e1", marginBottom: "0.5rem" }}>Ask any enterprise question</h3>
              <p>Answers are strictly grounded in indexed multi-tenant SOPs and documentation.</p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                maxWidth: "75%",
                padding: "1rem 1.25rem",
                borderRadius: "0.75rem",
                backgroundColor: msg.role === "user" ? "#2563eb" : "#1e293b",
                border: msg.role === "assistant" && !msg.is_grounded ? "1px solid #ef4444" : "1px solid #334155",
              }}
            >
              <div style={{ fontSize: "0.75rem", fontWeight: "bold", marginBottom: "0.25rem", color: msg.role === "user" ? "#bfdbfe" : "#94a3b8" }}>
                {msg.role === "user" ? "You" : "AI Knowledge Assistant"}
              </div>
              <div style={{ whiteSpace: "pre-wrap", lineHeight: "1.5" }}>{msg.content}</div>

              {/* Citations List */}
              {msg.citations && msg.citations.length > 0 && (
                <div style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: "1px solid #334155" }}>
                  <div style={{ fontSize: "0.75rem", fontWeight: "bold", color: "#38bdf8", marginBottom: "0.5rem" }}>Sources & Citations ({msg.citations.length}):</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                    {msg.citations.map((c, i) => (
                      <button
                        key={c.chunk_id}
                        onClick={() => setSelectedCitation(c)}
                        style={{
                          fontSize: "0.75rem",
                          padding: "0.25rem 0.5rem",
                          borderRadius: "0.25rem",
                          backgroundColor: "#0f172a",
                          border: "1px solid #38bdf8",
                          color: "#38bdf8",
                          cursor: "pointer",
                        }}
                      >
                        [Source {i + 1}] {c.document_title || "Document"} (p.{c.page_number || 1})
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div style={{ alignSelf: "flex-start", padding: "1rem", borderRadius: "0.75rem", backgroundColor: "#1e293b", color: "#94a3b8" }}>
              Synthesizing grounded response...
            </div>
          )}
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} style={{ padding: "1.5rem 2rem", borderTop: "1px solid #334155", display: "flex", gap: "1rem" }}>
          <input
            type="text"
            placeholder="Type your question (e.g. How to resolve hydraulic pump ERR-505?)..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            style={{
              flex: 1,
              padding: "0.875rem 1.25rem",
              borderRadius: "0.5rem",
              backgroundColor: "#1e293b",
              border: "1px solid #475569",
              color: "#f8fafc",
              outline: "none",
            }}
          />
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: "0.875rem 1.75rem",
              borderRadius: "0.5rem",
              backgroundColor: "#2563eb",
              color: "#ffffff",
              fontWeight: "600",
              border: "none",
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            Send
          </button>
        </form>
      </div>

      {/* Citation Inspector Drawer */}
      {selectedCitation && (
        <div style={{ width: "350px", borderLeft: "1px solid #334155", padding: "1.5rem", backgroundColor: "#0f172a", overflowY: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: "bold", color: "#38bdf8" }}>Citation Detail</h3>
            <button onClick={() => setSelectedCitation(null)} style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "1.25rem" }}>&times;</button>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", fontSize: "0.875rem" }}>
            <div><strong style={{ color: "#64748b" }}>Document:</strong> <div>{selectedCitation.document_title || selectedCitation.document_id}</div></div>
            <div><strong style={{ color: "#64748b" }}>Section:</strong> <div>{selectedCitation.section_title || "Overview"}</div></div>
            <div><strong style={{ color: "#64748b" }}>Page:</strong> <div>{selectedCitation.page_number || 1}</div></div>
            <div><strong style={{ color: "#64748b" }}>Relevance Score:</strong> <div>{(selectedCitation.relevance_score * 100).toFixed(1)}%</div></div>
            <div style={{ marginTop: "0.5rem" }}>
              <strong style={{ color: "#64748b" }}>Snippet:</strong>
              <div style={{ marginTop: "0.25rem", padding: "0.75rem", borderRadius: "0.375rem", backgroundColor: "#1e293b", color: "#cbd5e1", fontSize: "0.85rem", lineHeight: "1.4" }}>
                {selectedCitation.snippet}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
