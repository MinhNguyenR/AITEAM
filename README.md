# 🤖 AI Team Blueprint

**Version 6.2.0** | Enterprise-grade **multi-agent LLM orchestration framework** with **23 specialized agents**, intelligent task routing across 4 complexity tiers, and real-time cost/token monitoring.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[![Agents](https://img.shields.io/badge/Agents-23_%285_Implemented%29-orange)]()
[![Models](https://img.shields.io/badge/Models-70%2B_via_OpenRouter-brightgreen)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Production-Ready](https://img.shields.io/badge/Status-Production--Ready-green)]()

---

## 📖 Quick Navigation

- [🎯 Overview](#-overview)
- [🕹️ Agent System](#-agent-system)
- [✨ Features](#-features)
- [📦 Installation](#-installation)
- [🚀 Quick Start](#-quick-start)
- [📚 Usage](#-usage)
- [🔧 Configuration](#-configuration)
- [📊 Task Tiers](#-task-tiers)
- [💰 Costs & Budget](#-costs--budget)
- [📈 Project Status](#-project-status)
- [🤝 Contributing](#-contributing)
- [❓ FAQ](#-faq)
- [Repository layout](#repository-layout)

---

## Repository layout

Entrypoint: `aiteam` → `core.cli.app:main_loop`. Full map: [`docs/REPO_LAYOUT.md`](docs/REPO_LAYOUT.md).

| Area | Role |
|------|------|
| [`core/bootstrap.py`](core/bootstrap.py) | `ensure_project_root()` / `REPO_ROOT`; path helpers in [`core/paths.py`](core/paths.py). |
| [`scripts/run_aiteam.py`](scripts/run_aiteam.py) | Dev runner (`python scripts/run_aiteam.py`). |
| [`core/resources/fonts/`](core/resources/fonts/) | Bundled Inter fonts for PDF/dashboard. |
| [`agents/`](agents/) | Agent implementations; LangGraph graph under [`agents/team_map/`](agents/team_map/). |
| [`core/cli/`](core/cli/) | Menu shell: [`app.py`](core/cli/app.py), [`state.py`](core/cli/state.py), prompts/registry; **flows** in [`core/cli/flows/`](core/cli/flows/) (ask/start/context/…); **UI chrome** in [`core/cli/chrome/`](core/cli/chrome/) (console helpers, palette, help); **workflow** in [`core/cli/workflow/runtime/`](core/cli/workflow/runtime/) (session, runner, checkpoints) and [`core/cli/workflow/tui/`](core/cli/workflow/tui/) (monitor, list view). |
| [`core/domain/`](core/domain/) | Prompts, routing map, pipeline/task state shared with agents. |
| [`core/dashboard/`](core/dashboard/) | Usage dashboard (Rich); exports: [`report_model.py`](core/dashboard/report_model.py) (single `UsageReport`), [`text_export.py`](core/dashboard/text_export.py) / [`report_txt_format.py`](core/dashboard/report_txt_format.py) (TXT), [`pdf_export.py`](core/dashboard/pdf_export.py) (PDF), [`exporters.py`](core/dashboard/exporters.py) (XLSX KPI + sheets). |
| [`core/config/`](core/config/), [`core/storage/`](core/storage/) | Configuration and persistence. |
| [`core/api/`](core/api/) | Reserved placeholder for v7.0 REST surface. |
| [`utils/tracker/`](utils/tracker/) | Usage logging, budgets, rollups (package; import as `from utils import tracker` or `from utils.tracker import …`). |
| [`docs/`](docs/) | Security, layout, notes under [`docs/notes/`](docs/notes/), optional [`docs/skills_admin/`](docs/skills_admin/). |
| [`tests/`](tests/) | Pytest; optional dev deps: `pip install -e ".[dev]"`. |

---

## 🎯 Overview

**AI Team Blueprint** automatically routes tasks to optimal agents from a team of 23 specialists:

1. **Analyzes** task complexity (simple Q&A vs distributed systems)
2. **Routes** to best-fit tier (LOW/MEDIUM/EXPERT/HARD)
3. **Generates** architectural plans via LangGraph pipeline
4. **Enforces** strict budget & token controls
5. **Approves** plans via human review gates
6. **Executes** approved tasks (planned: v6.3)

### Why AI Team?

- 🧠 **23 Specialized Agents**: Each optimized for specific roles
- 🎯 **Intelligent Routing**: Automatic tier classification & model selection
- 💰 **Cost-Optimized**: Smart model selection saves 15x on simple tasks
- 📊 **Real-Time Monitoring**: Live dashboard with token & cost tracking
- 🔄 **Resumable Workflows**: LangGraph checkpoints enable recovery
- 🏗️ **Architecture-First**: Plans before execution
- 🔒 **Enterprise Security**: Budget guards, API key protection, hardware awareness

---

## 🕹️ Agent System

### 23 Agents Across 5 Tiers

**Classification** (1):
- Ambassador (gpt-5.4-nano): Parses task & classifies tier

**Leadership** (4):
- LeaderLow (xiaomi/mimo): Fast context for LOW tier
- LeaderMedium (minimax-m2.5): Standard context for MEDIUM tier
- LeaderHigh (google/gemini-3.1-pro): Complex architectures for HIGH tier
- Commander (claude-opus-4.6): Super-agent coordinator (v7.0)

**Specialists** (7):
- Expert (kimi-k2.5): 1M-token deep-dive expert
- Researcher, Browser, ToolCurator: Support agents
- FixWorker, Secretary, FinalReviewer: Quality roles

**Execution** (9):
- Worker, CodeGen, TestAgent, Reviewer, Debugger, Validator, Optimizer, Documenter, Trainer

**Chat** (2):
- ChatStandard, ChatThinking

**Status:**
- ✅ 5 Implemented (Ambassador, Leaders, Expert)
- 🟡 2 In-Dev (Researcher, Browser)
- ❌ 16 Planned (v6.3-v7.0)

### Agent Roles

**Ambassador**
- Model: gpt-5.4-nano ($0.0001/task)
- Role: Entry point for all workflows
- Input: Task description
- Output: Tier classification + requirements

**Leaders (Low/Med/High)**
- Cost: $0.02-0.10 per use
- Output: context.md with architectural plan
- Gate: Requires human approval

**Expert**
- Model: kimi-k2.5 (1M context tokens)
- Cost: $0.20-0.50 per use
- Modes: SOLO (standalone) or COPLAN (validate LeaderHigh)

### Workflow

```
Task → Ambassador → Tier Classification
         ↓
       ┌─LOW─┬──MEDIUM──┬──EXPERT──┬──HARD──┐
       ↓     ↓          ↓          ↓        ↓
    LeaderLow LeaderMed Expert  LeaderHigh+Expert
       ↓     ↓          ↓          ↓        ↓
    context.md [all routes generate context.md]
       ↓     ↓          ↓          ↓        ↓
       └─────┴──────────┼──────────┴────────┘
               ↓
           HUMAN REVIEW GATE
           [Accept|Regenerate|Decline]
               ↓
          Workers Execute (v6.3+)
```

---

## ✨ Features

### ✅ Implemented (v6.2)

| Feature | Status | Notes |
|---------|--------|-------|
| 23-Agent Registry | ✅ | All agents registered with clear interfaces |
| 4-Tier Classification | ✅ | LOW/MEDIUM/EXPERT/HARD automatic routing |
| OpenRouter Integration | ✅ | 70+ models, live pricing sync |
| Budget Guard System | ✅ | Dual-level: session + task limits |
| Real-Time TUI Monitor | ✅ | Textual-based dashboard |
| Context Generation | ✅ | LLM-generated architectural plans |
| Human Approval Gate | ✅ | Interrupt-before pattern |
| Knowledge Store | ✅ | SQLite semantic search |
| Hardware Detection | ✅ | Auto-detect GPU/CUDA/VRAM |
| Cost Dashboard | ✅ | Per-model spending, token breakdown |

### 🟡 In Development (v6.3-v7.0)

| Feature | Timeline | Notes |
|---------|----------|-------|
| Worker Execution | v6.3 | CodeGen, Testing, etc. |
| Code Generation | v6.3 | Synthesis from context.md |
| Bug Fix Automation | v6.4 | Error detection + repair |
| Full Agent Sync | v7.0 | All 23 agents working together |

---

## 📦 Installation

### Requirements

- Python 3.10+
- 8GB RAM minimum (16GB+ recommended)
- GPU optional (NVIDIA CUDA 11.8+ auto-detected)

### Setup

```bash
# Clone
git clone https://github.com/your-org/ai-team.git
cd ai-team

# Virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install
pip install -e .

# Configure
export OPENROUTER_API_KEY="your_key_here"
# or create .env: OPENROUTER_API_KEY=sk_...

# Verify
aiteam --help
```

---

## 🚀 Quick Start

### Run CLI

```bash
aiteam
```

Main menu options:
- `1/start` - Begin workflow
- `2/check` - Review generated context
- `3/status` - Check API & hardware
- `4/info` - System information
- `5/dashboard` - View costs & tokens
- `6/settings` - Configure
- `7/help` - Help
- `8/workflow` - Monitor pipeline
- `9/exit` - Exit

### Example: Submit Task

```
> 1  # Start workflow
📝 Describe your task:
> Build FastAPI microservice with JWT + PostgreSQL

⏳ Analyzing...
✅ Classified as MEDIUM tier
✅ Context generated (25s, $0.07)

Accept context? [1] Yes [2] Regenerate [3] Decline
> 1  # Approve
```

### Example: Check Costs

```
> 5  # Dashboard
╔════════════════════════════╗
║ Wallet: $127.43            ║
║ Session Spent: $2.15       ║
║ Session Budget: $10.00     ║
║ Tasks Completed: 3         ║
╚════════════════════════════╝
```

---

## 📚 Usage

### Configuration

```bash
# Environment variables (.env or export)
OPENROUTER_API_KEY=sk_...           # Required
MAX_VRAM_LIMIT=12                   # GPU VRAM cap (GB)
SESSION_BUDGET_LIMIT=10.0           # Session spending cap ($)
TASK_BUDGET_LIMIT=5.0               # Per-task spending cap ($)
AI_TEAM_CACHE_ROOT=/path            # Custom cache directory
AI_TEAM_PROFILE=production          # production|development|debug
```

### Settings Menu

```
> 6  # Settings
- Default tier for ambiguous tasks
- Max tokens per task
- Streaming output (enabled/disabled)
- Budget alert threshold
- Log verbosity
- Language (English/Vietnamese)
```

---

## 📊 Task Tiers

| Tier | Complexity | Duration | Cost | Models | Use Cases |
|------|-----------|----------|------|--------|-----------|
| **LOW** | Simple | <5s | $0.02 | nano models | Q&A, bugs, docs |
| **MEDIUM** | Standard | 20-45s | $0.10 | minimax-m2.5 | APIs, pipelines, RAG |
| **EXPERT** | Complex | 1-2 min | $0.30 | kimi, gemini | Microservices, ML arch |
| **HARD** | Specialized | 2-3 min | $0.60 | High-end | CUDA, GPU optimization |

### Classification Examples

```
"What is REST?" → LOW ($0.02)
"Build FastAPI CRUD" → MEDIUM ($0.10)
"Design SaaS architecture" → EXPERT ($0.30)
"Optimize GPU kernels" → HARD ($0.60)
```

### Manual Override

```bash
> 6  # Settings
> Choose default tier: [1] LOW [2] MEDIUM [3] EXPERT [4] HARD
> 3  # Force EXPERT tier for all tasks
```

---

## 💰 Costs & Budget

### Cost Breakdown by Tier

| Tier | Ambassador | Leader | Specialists | Total | Time |
|------|-----------|--------|-------------|-------|------|
| LOW | $0.0001 | $0.02 | — | $0.02 | 5-10s |
| MEDIUM | $0.0001 | $0.03 | $0.05 | $0.10 | 20-45s |
| EXPERT | $0.0001 | — | $0.30 | $0.30 | 1-2 min |
| HARD | $0.0001 | $0.10 | $0.50 | $0.60 | 2-3 min |

### Budget Guard

**Two-Level Protection:**
- Session limit: Total spend cap for entire session
- Task limit: Per-task spending cap

```bash
# Set budgets
export SESSION_BUDGET_LIMIT=10.0   # Max $10 per session
export TASK_BUDGET_LIMIT=5.0       # Max $5 per task
```

**Dashboard shows:**
- Wallet balance & monthly spend
- Session spent vs budget
- Current task cost breakdown
- Token counts (input/output)

### Cost Optimization

1. **Tier Selection**: 15x savings (LOW vs EXPERT)
2. **Knowledge Reuse**: 40% reduction on similar tasks
3. **Batch Processing**: 30% overhead savings  
4. **Model Override**: Custom model selection
5. **Cache Warming**: Knowledge base hits reduce LLM calls

---

## 💾 Storage & Knowledge

- **Knowledge Store**: SQLite semantic search (CompressedBrain)
- **GraphRAG Store**: Temporary workspace graph + FTS index for codebase-wide retrieval
- **Chat History**: Persisted conversations across sessions
- **State Persistence**: Task metadata, costs, hardware info, timestamps
- **Context Archive**: Generated .md files for each task

Location: `~/.aiteam/cache/`

---

## 📈 Project Status

### Completion: 77% (48/62 files)

| Component | Status | Progress |
|-----------|--------|----------|
| Agents | In Progress | 5/23 implemented |
| Core System | Stable | 95% |
| CLI & UI | Complete | 100% |
| Storage | Complete | 100% |
| Config | Complete | 100% |
| Budget/Cost | Complete | 100% |
| Testing | Partial | 25% |
| Docs | Excellent | 95% |

### Agent Implementation Timeline

**Phase 1 - ACTIVE** ✅ (v6.2)
- [x] Ambassador, LeaderLow/Med/High, Expert

**Phase 2** 🟡 (v6.3 - June 2026)
- [ ] Worker execution, Researcher, Browser, CodeGen, TestAgent

**Phase 3** ⏳ (v6.4-v7.0)
- [ ] Remaining agents (13 total)

### Roadmap

- **v6.2** (Current): Context generation + TUI monitoring
- **v6.3** (Q2 2026): Worker execution + code generation
- **v6.4** (Q3 2026): Bug fixes + optimization agents
- **v6.5** (Q4 2026): ML pipeline + documentation
- **v7.0** (Q1 2027): All 23 agents, enterprise features

---

## 🤝 Contributing

We welcome contributions!

### Contribute

```bash
# Fork & clone
git clone https://github.com/your-fork/ai-team.git

# Branch
git checkout -b feature/implement-worker-agent

# Test
python tests/test_leader_flow.py

# Submit PR
git commit -m "feat: implement Worker agent"
git push origin feature/implement-worker-agent
```

### Areas for Help

- Worker agents (CodeGen, TestAgent, etc.)
- Testing & validation
- Documentation & tutorials
- Performance optimization
- UI/UX enhancements

---

## ❓ FAQ

**Q: How much does it cost?**
- LOW tier: ~$0.02 per task
- MEDIUM: ~$0.10
- EXPERT: ~$0.30
- HARD: ~$0.60

**Q: Can I set spending limits?**
- Yes: SESSION_BUDGET_LIMIT and TASK_BUDGET_LIMIT environment variables

**Q: How do I add my own model?**
- Edit `core/config/registry.py` and add to MODEL_REGISTRY

**Q: Does it work without GPU?**
- Yes, auto-falls back to CPU if CUDA unavailable

**Q: How long does context generation take?**
- LOW: 5-10 seconds
- MEDIUM: 20-45 seconds
- EXPERT: 1-2 minutes
- HARD: 2-3 minutes

**Q: Can I resume interrupted workflows?**
- Yes, LangGraph checkpointing enables recovery

**Q: Is there a knowledge base?**
- Yes, CompressedBrain SQLite store learns from every task

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/ai-team/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/ai-team/discussions)
- **Documentation**: Full docs at [docs.aiteam.dev](https://docs.aiteam.dev)

---

## 📝 License

MIT License. See [LICENSE](LICENSE) for details.

---

**Built with LangGraph, OpenRouter, Textual, Rich**

*Last updated: April 14, 2026*
