<div align="center">

<!--![MCP Servers Collection](image_placeholder) -->


# 🔌 MCP Servers Collection

*Production-ready [Model Context Protocol](https://modelcontextprotocol.io/introduction) servers with standardized architecture*

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://docker.com)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.12+-yellow?logo=python)](https://python.org)
[![Cursor](https://img.shields.io/badge/CursorIDE-Compatible-blue)](https://www.cursor.com/)
[![Claude Desktop](https://img.shields.io/badge/ClaudeDesktop-Compatible-orange)](https://claude.ai/)
[![LangChain](https://img.shields.io/badge/LangChain-Compatible-green)](https://www.langchain.com/)


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


## 🛠️ Available Servers

Please check the latest [Release Doc](https://github.com/Xyber-Labs/mcp-servers/releases) to see the full list of available MCP-servers

## 🚀 Quick Start

### 📋 Prerequisites

- 🐳 Docker and Docker Compose
- ⚙️ Service-specific `.env` setup (see individual service READMEs)

### 🏃‍♂️ Running Services

```bash
# 🐙 Using Docker Compose (recommended)
docker-compose up -d                        # All services
docker-compose up mcp-server-youtube -d     # Specific service

# 🐳 Using Docker directly
cd mcp-server-youtube
docker build -t mcp-server-youtube .
docker run -p 8000:8000 --env-file .env mcp-server-youtube
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
