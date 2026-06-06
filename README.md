# Ai-Agent-2.0
A modular multi-agent system for creative strategy &amp; production. Bridges social media management and high-end creative execution (design, motion, scripts) using Model Context Protocol (MCP) for tool extensibility and RAG for continuous learning from your past assets.

# Creative Agent: Social & Design Intelligence

This repository houses the development of a specialized AI agent system designed to bridge the gap between **Social Media Strategy** and **Creative Production** (Design, Motion Graphics, and Video Scripting). 

#  Vision
To build an agentic system that acts as a lead creative strategist, capable of:
1. **Social Intelligence:** Analyzing live social media pages and trends to generate actionable reports.
2. **Creative Execution:** Applying high-level design theory to video scripts and motion graphics direction.
3. **Continuous Growth:** Evolving through a modular "skills" architecture that allows for tool integration.

#  Architecture
We are utilizing a **Multi-Agent Supervisor Pattern** supported by two critical technical pillars:

- **Model Context Protocol (MCP):** We will use frameworks that support MCP (like Mastra or Claude's implementation) to connect the agent to data sources or tools (local design asset folders, Notion, Slack) as if they were native plugins.
- **Vector Memory (RAG):** Instead of retraining, the agent will utilize a "Library" powered by a Vector Database (like Pinecone or a local store). Every project—including the brief, design files, and final video script—will be saved to this "Memory," allowing the AI to reference your past real-life work for future designs.
- **Supervisor Agent:** Orchestrates tasks and delegates to specialized sub-agents.

#  Repository Structure
```text
/agents          # Definitions for specific specialized agents
/tools           # Python scripts/plugins (Social parser, Design theory evaluator, etc.)
/knowledge       # Vector database/Markdown library for 'Golden Standard' creative assets
/prompts         # System instructions and prompt templates
/docs            # Design theory guidelines and project requirements
main.py          # Orchestration logic
