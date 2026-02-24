<div align="center">

<!--![MCP Servers Collection](image_placeholder) -->


# 🔌 MCP Servers Collection

*Production-ready [Model Context Protocol](https://modelcontextprotocol.io/introduction) servers with standardized architecture*

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://docker.com)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.12+-yellow?logo=python)](https://python.org)
[![x402](https://img.shields.io/badge/x402-v2.0-purple)](https://x402.org)
[![Cursor](https://img.shields.io/badge/CursorIDE-Compatible-blue)](https://www.cursor.com/)
[![Claude Desktop](https://img.shields.io/badge/ClaudeDesktop-Compatible-orange)](https://claude.ai/)
[![LangChain](https://img.shields.io/badge/LangChain-Compatible-green)](https://www.langchain.com/)

**Supported Payment Chains**

[![Base](https://img.shields.io/badge/Base-0052FF?logo=coinbase&logoColor=white)](https://base.org)
[![Solana](https://img.shields.io/badge/Solana-9945FF?logo=solana&logoColor=white)](https://solana.com)
[![Avalanche](https://img.shields.io/badge/Avalanche-E84142?logo=avalanche&logoColor=white)](https://avax.network)
[![BNB Chain](https://img.shields.io/badge/BNB_Chain-F0B90B?logo=binance&logoColor=black)](https://bnbchain.org)
[![Polygon](https://img.shields.io/badge/Polygon-8247E5?logo=polygon&logoColor=white)](https://polygon.technology)
[![SKALE](https://img.shields.io/badge/SKALE-000000?logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTIgMjRjNi42MjcgMCAxMi01LjM3MyAxMi0xMlMxOC42MjcgMCAxMiAwIDAgNS4zNzMgMCAxMnM1LjM3MyAxMiAxMiAxMnoiIGZpbGw9IiMwMDAiLz48L3N2Zz4=&logoColor=white)](https://skale.space)
[![Sei](https://img.shields.io/badge/Sei-FF0000?logoColor=white)](https://sei.io)


</div>

## 🎯 **Why Choose Our MCP Servers?**

### 🚨 **Community MCP problems**

If you've tried working with community MCP servers, you've probably encountered these common pain points:

- **Inconsistent Architecture**: Every server has a different file structure, making it impossible to maintain a unified codebase
- **Missing Features**: Some servers only support SSE, others only stdio - forcing you to choose between functionality and compatibility
- **Abandoned Projects**: Many servers haven't been updated since MCP's early days, leaving you stranded with outdated implementations
- **No Standards**: Lack of best practices means you're constantly reinventing the wheel for each new server

### 💡 **We've Solved These Problems**

This repository was built from the ground up to eliminate these frustrations:

- **🏗️ Standardized Architecture**: Every server follows the same proven structure, which enforces all servers to:
- **🔧 Have Full Protocol Support**: support SSE, streamable http, stdio transports, giving you maximum flexibility
- **⚡ Be Modern & Maintained**: built with the latest MCP/FastMCP specifications and actively maintained
- **📋 Have Best Practices Built-In**: implement industry-standard patterns - no more guessing 
- **🛠️ Be Production-Ready**: fully tested, documented, monitored, securely configured, and quality-checked with automated linting, type-checking, and environment validation
- **💰 Monetization-Ready**: Built-in support for the [x402 payment protocol](https://x402.org) to monetize endpoints with zero code changes
- **🐳 Effortless Deployed**: implement multi-stage Docker builds, Docker Compose integration and optimized images for production or local dev
- **📚 Convinient for developers**: have template-based rapid prototyping, hot-reload support, and clear documentation/examples
- **🔒 Secure & Reliable**: inlcude environment-based credential management, health monitoring, and robust error handling

### 🎯 **Why This Matters for You**

**For Developers**: Skip the learning curve - once you understand one of our servers, you can instantly work with any of them. Perfect integration with CursorIDE, Claude Desktop and Langgraph

**For Teams**: Maintain consistency across your entire MCP infrastructure with our standardized approach

**For Production**: Deploy with confidence knowing each server follows proven patterns and includes comprehensive testing

**For Custom Development**: Use our `mcp-server-template` to create your own servers in minutes, not hours

## 🛠️ Live Servers

| Server | Live URL | Description |
|--------|----------|------------|
| **Quill** | [https://mcp-quill.xyber.inc](https://mcp-quill.xyber.inc/docs) | Token security analysis for EVM & Solana chains |
| **Lurky** | [https://mcp-lurky.xyber.inc](https://mcp-lurky.xyber.inc/docs) | Twitter/X data access and analysis |
| **Tavily** | [https://mcp-tavily.xyber.inc](https://mcp-tavily.xyber.inc/docs) | Web-search capabilities |
| **YouTube** | [https://mcp-youtube.xyber.inc](https://mcp-youtube.xyber.inc/docs) | YouTube video data and transcripts |
| **GitParser** | [https://mcp-gitparser.xyber.inc](https://mcp-gitparser.xyber.inc/docs) | Git repositories parsing and analysis |
| **ArXiv** | [https://mcp-arxiv.xyber.inc](https://mcp-arxiv.xyber.inc/docs) | Searching & accessing arXiv papers |
| **Wikipedia** | [https://mcp-wikipedia.xyber.inc](https://mcp-wikipedia.xyber.inc/docs) | Wikipedia content access |

> 💡 All live servers support x402 payments on multiple networks, check the server's `/pricing` endpoint for the details

For the full list of available MCP servers (including self-hosted options), check the latest [Release Doc](https://github.com/Xyber-Labs/mcp-servers/releases)

## 🚀 Quick Start

### 📋 Prerequisites

- 🐳 Docker and Docker Compose
- ⚙️ Service-specific `.env` setup (see individual service READMEs)

### 🏃‍♂️ Running Services

```bash
# 🐙 Using Docker Compose (recommended)
docker-compose up -d                        # All services
docker-compose up mcp_server_youtube -d     # Specific service

# 🐳 Using Docker directly
cd mcp-server-youtube-v2
docker build -t mcp-server-youtube-v2 .
docker run -p 8000:8000 --env-file .env mcp-server-youtube-v2
```

## 📚 Documentation & Resources

- **[Contributing Guidelines](CONTRIBUTING.md)** - Development setup and workflow
- **[Individual Service READMEs](mcp-server-template/README.md)** - Service-specific documentation
- **[FastMCP Official Documentation](https://fastmcp.readthedocs.io/)** – FastMCP server and protocol reference
- **[Anthropic MCP Protocol Specification](https://modelcontextprotocol.io/introduction)** – Anthropic's MCP protocol docs
- **[Anthropic Official MCP servers repository](https://github.com/modelcontextprotocol/servers)** 
- **[License](./LICENSE)**


## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for:

- **Development setup** and environment configuration
- **Code standards** and quality requirements
- **Adding new services** using our template system
- **Testing guidelines** and best practices
- **Pull request workflow** and review process

## 🙏 Acknowledgments

Special thanks to:
- The **Model Context Protocol** community for the excellent specification
- **OpenAI** and **Anthropic** for pioneering MCP adoption
- All contributors and early adopters who provided feedback
- The open-source community for the amazing tools that make this possible

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

<div align="center">

**🌟 Star this repo if you find it useful! 🌟**

</div>
