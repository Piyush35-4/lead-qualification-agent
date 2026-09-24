# AI Lead Qualification & Follow-up Agent

An agentic AI MVP for conversational lead qualification and follow-up management.

The application uses **FastAPI, LangGraph, Groq, FastMCP, Pydantic, and SQLite** to conduct multi-turn conversations, assess leads, perform CRM actions through MCP tools, and generate contextual responses.

## Architecture

```text
User
  ↓
HTML / CSS / JavaScript
  ↓
FastAPI
  ↓
LangGraph
  ↓
Groq LLM
  ↓
Structured Lead Assessment
  ↓
MCP Client (stdio)
  ↓
FastMCP Server
  ↓
MCP Tools
  ├── search_products
  ├── get_lead
  ├── update_lead
  ├── create_followup
  └── handoff_to_human
  ↓
SQLite CRM