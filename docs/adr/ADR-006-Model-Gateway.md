# ADR-006: AI Model Gateway & Provider Abstraction

## Status
Accepted

## Context
Directly invoking specific LLM APIs (Ollama, OpenAI, Anthropic, Gemini, vLLM) across domain features hardcodes third-party dependencies and vendor lock-in into core business applications.

## Decision
Implement an **AI Model Gateway** with unified provider interfaces (`LLMProvider`, `EmbeddingProvider`, `RerankerProvider`, `VisionProvider`, `OCRProvider`).
- Business logic invokes capabilities (e.g. `CHAT_GENERATION`, `EMBEDDING`, `RERANKING`) mapped via configuration to target providers.
- Supports provider fallback, request tracing, token tracking, and switching between local Ollama / vLLM and cloud providers without changing domain logic.

## Consequences
### Positive
- Total vendor independence.
- Capability-based routing and seamless fallback handling.
### Negative
- Requires maintaining generic provider wrapper contracts.
