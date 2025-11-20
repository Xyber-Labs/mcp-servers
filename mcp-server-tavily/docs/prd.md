# Tavily MCP Server - Product Requirements Document

## Overview
The Tavily MCP Server provides AI-powered web search capabilities through REST APIs, MCP tools, and hybrid endpoints. All public endpoints require x402 payment, enabling monetization of search operations.

## Target Personas
- **AI Agents**: Language models and autonomous agents requiring real-time web search
- **Developers**: Building applications that integrate Tavily search functionality
- **Enterprise Users**: Organizations needing programmatic access to Tavily's search API

## Core Capabilities

### 1. Web Search (Hybrid Endpoint)
- **Description**: Performs intelligent web search using Tavily's AI-powered search engine
- **Access**: Available via both REST API (`/hybrid/search`) and MCP tools
- **Payment**: Required via x402 protocol
- **Input**: Search query string, optional max_results parameter
- **Output**: Formatted search results with titles, URLs, and content snippets
- **Use Cases**: 
  - AI agents researching topics
  - Applications requiring current web information
  - Content discovery and aggregation

### 2. Search Configuration (MCP-Only Tool)
- **Description**: Utility tool for AI agents to configure search parameters
- **Access**: MCP-only (not exposed as REST endpoint)
- **Payment**: Free (utility function)
- **Use Cases**: Agents adjusting search depth, topic filters, or result formatting

### 3. Health Check (API-Only Endpoint)
- **Description**: Server health and status monitoring
- **Access**: REST API only (`/api/health`)
- **Payment**: Free (operational endpoint)
- **Use Cases**: Load balancers, monitoring systems, deployment health checks

### 4. Admin Logs (API-Only Endpoint)
- **Description**: Retrieves server logs for administrative purposes
- **Access**: REST API only (`/api/admin/logs`)
- **Payment**: Required via x402 protocol
- **Use Cases**: Debugging, monitoring, compliance auditing

## Authentication & Secrets
- Tavily API key passed via `Tavily-Api-Key` HTTP header per request
- Server does not store API keys; clients must provide their own Tavily credentials
- Missing or invalid API keys result in 400/503 responses

## Payment Model
- All public search endpoints require x402 payment
- Multiple payment options supported (different tokens/networks)
- Free endpoints: health check, utility tools
- Paid endpoints: web search, admin logs

## Success Metrics
- Search latency < 2 seconds (p95)
- Payment verification success rate > 99%
- API uptime > 99.9%
- Search result relevance (measured via user feedback)

## Dependencies
- Tavily AI API (external service)
- x402 facilitator (payment verification)
- FastAPI framework
- FastMCP for MCP protocol support

