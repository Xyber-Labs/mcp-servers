# ArXiv MCP Server - Product Requirements Document

## Overview
The ArXiv MCP Server provides academic paper search and retrieval capabilities through REST APIs, MCP tools, and hybrid endpoints. All public endpoints require x402 payment, enabling monetization of academic research access.

## Target Personas
- **AI Agents**: Language models and research assistants requiring academic paper access
- **Researchers**: Academics and students needing programmatic paper retrieval
- **Developers**: Building applications that integrate ArXiv search functionality

## Core Capabilities

### 1. Paper Search (Hybrid Endpoint)
- **Description**: Searches ArXiv for academic papers, downloads PDFs, and extracts text content
- **Access**: Available via both REST API (`/hybrid/search`) and MCP tools
- **Payment**: Required via x402 protocol
- **Input**: Search query string, optional max_results and max_text_length parameters
- **Output**: Formatted paper results with metadata (title, authors, summary) and extracted text
- **Use Cases**:
  - AI agents conducting literature reviews
  - Research applications aggregating academic content
  - Automated paper discovery and analysis

### 3. Health Check (API-Only Endpoint)
- **Description**: Server health and status monitoring
- **Access**: REST API only (`/api/health`)
- **Payment**: Free (operational endpoint)
- **Use Cases**: Load balancers, monitoring systems, deployment health checks

## Authentication & Secrets
- No external API keys required (ArXiv is publicly accessible)
- PDF processing and text extraction handled server-side
- Rate limiting managed via x402 payment model

## Payment Model
- All public search endpoints require x402 payment
- Multiple payment options supported (different tokens/networks)
- Free endpoints: health check, utility tools
- Paid endpoints: paper search with PDF extraction, admin logs
- Pricing reflects computational cost of PDF download and text extraction

## Success Metrics
- Search latency < 5 seconds (p95) including PDF processing
- Payment verification success rate > 99%
- API uptime > 99.9%
- PDF extraction success rate > 95%
- Text extraction accuracy (measured via manual review)

## Dependencies
- ArXiv API (public, no authentication)
- PyMuPDF library (PDF text extraction)
- x402 facilitator (payment verification)
- FastAPI framework
- FastMCP for MCP protocol support

