"use client";

import React from "react";
import ReactMarkdown from "react-markdown";

interface MarkdownRendererProps {
  content: string;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="markdown-content" style={{ fontSize: "14px", lineHeight: "1.6", color: "inherit" }}>
      <ReactMarkdown
        components={{
          p: ({ children }) => (
            <p style={{ margin: "0 0 10px 0", lineHeight: "1.6" }}>{children}</p>
          ),
          strong: ({ children }) => (
            <strong style={{ fontWeight: "700", color: "inherit" }}>{children}</strong>
          ),
          em: ({ children }) => (
            <em style={{ fontStyle: "italic" }}>{children}</em>
          ),
          ol: ({ children }) => (
            <ol style={{ paddingLeft: "22px", margin: "8px 0 12px 0", display: "flex", flexDirection: "column", gap: "6px" }}>
              {children}
            </ol>
          ),
          ul: ({ children }) => (
            <ul style={{ paddingLeft: "22px", margin: "8px 0 12px 0", display: "flex", flexDirection: "column", gap: "6px" }}>
              {children}
            </ul>
          ),
          li: ({ children }) => (
            <li style={{ lineHeight: "1.55" }}>{children}</li>
          ),
          h1: ({ children }) => (
            <h1 style={{ fontSize: "18px", fontWeight: "700", margin: "12px 0 6px 0" }}>{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 style={{ fontSize: "16px", fontWeight: "700", margin: "10px 0 6px 0" }}>{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 style={{ fontSize: "15px", fontWeight: "700", margin: "8px 0 4px 0" }}>{children}</h3>
          ),
          code: ({ className, children }) => {
            const isBlock = className && className.startsWith("language-");
            if (isBlock) {
              return (
                <code
                  style={{
                    display: "block",
                    backgroundColor: "#1a1a1a",
                    color: "#f8fafc",
                    padding: "12px 16px",
                    borderRadius: "6px",
                    overflowX: "auto",
                    fontFamily: "monospace",
                    fontSize: "13px",
                    lineHeight: "1.4",
                    margin: "8px 0",
                  }}
                >
                  {children}
                </code>
              );
            }
            return (
              <code
                style={{
                  backgroundColor: "rgba(0, 0, 0, 0.06)",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  fontFamily: "monospace",
                  fontSize: "13px",
                  color: "inherit",
                }}
              >
                {children}
              </code>
            );
          },
          blockquote: ({ children }) => (
            <blockquote
              style={{
                borderLeft: "3px solid var(--color-primary)",
                paddingLeft: "12px",
                margin: "8px 0",
                color: "var(--text-secondary)",
                fontStyle: "italic",
              }}
            >
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
