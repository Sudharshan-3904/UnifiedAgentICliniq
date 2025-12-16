# MedToolAgent

> An AI-powered medical assistant system with integrated PubMed search, semantic ranking, safety verification, and multi-agent orchestration.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.0.20%2B-orange)](https://github.com/langchain-ai/langgraph)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)](https://streamlit.io/)

## 🎯 Overview

MedToolAgent is a sophisticated medical AI assistant that combines:
- **Multi-Agent Architecture**: Orchestrated workflow with prompt building, LLM inference, safety checking, and recovery
- **PubMed Integration**: Real-time medical literature search with semantic ranking
- **Safety-First Design**: All responses validated for medical accuracy
- **Tool Integration**: Access to PubMed, EHR data, and clinical guidelines
- **Intelligent Recovery**: Automatic retry mechanism when safety checks fail

## ✨ Key Features

### 🔬 Advanced PubMed Search
- Search millions of medical articles via NCBI Entrez API
- Fetch complete article details (title, abstract, full text, artifacts)
- **Semantic Ranking**: AI-powered relevance ranking using Google Gemini embeddings + FAISS
- Extract tables, figures, and supplementary materials
- Configurable result count and filtering

### 🛡️ Safety Verification
- Dedicated safety agent validates all responses
- Checks for medical accuracy and hallucinations
- Flags unsafe recommendations
- Detailed safety reports for transparency

### 🔄 Recovery Mechanism
- Automatic retry when safety checks fail
- Provides specific feedback to guide corrections
- Configurable retry limits
- Maintains conversation context

### 💬 Multi-Turn Conversations
- Session-based checkpointing
- Maintains context across interactions
- Thread-based conversation management

Usage notes:
- The backend accepts `thread_id` with `/run` requests; if omitted a new `thread_id` will be created and returned.
- To reset a conversation, POST `/run` with `{ "thread_id": "...", "reset": true }`.
- The Streamlit frontend automatically persists the `thread_id` per browser session.

### 🎯 Conditional Tool Calling
- **Smart Tool Selection**: PubMed tool only invoked when truly needed
- **Efficiency**: Faster responses for general medical questions
- **Cost Optimization**: Reduces unnecessary API calls and embeddings
- **Intelligent Routing**: Agent analyzes query intent before calling tools

### 🔄 Iterative Refinement Loop
- **Self-Correction**: Agent critiques and improves its own responses
- **Quality Assurance**: Ensures answers are direct, complete, and relevant
- **Feedback Loop**: Multi-step refinement process before output

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                       │
│                      (Port 8501)                            │
└─────────────────────────────────────────────────────────────┘
                           │ HTTP/REST
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                          │
│                      (Port 8000)                            │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              LangGraph Agent Workflow                  │ │
│  │                                                        │ │
│  │  Prompt Builder → LLM Agent → Refinement Agent         │ │
│  │                      ↓            ↓                    │ │
│  │                   Tools      Safety Agent              │ │
│  │                      ↑            ↓                    │ │
│  │                      └──────── recovery ───────────────┘ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              External Services                              │
│  • Ollama (gemma2:2b)  • NCBI PubMed  • Google Gemini       │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
MedToolAgent/
├── backend/                      # Python FastAPI backend
│   ├── src/
│   │   ├── agent/               # LangGraph workflow
│   │   │   ├── graph.py         # Workflow definition
│   │   │   ├── nodes.py         # Agent nodes
│   │   │   └── state.py         # State schema
│   │   ├── api/
│   │   │   └── server.py        # FastAPI endpoints
│   │   ├── tools/
│   │   │   ├── base.py          # Tool definitions
│   │   │   ├── pubmed_fetcher.py # PubMed search engine
│   │   │   └── mcp_server.py    # MCP integration
│   │   ├── config/
│   │   │   └── settings.py      # Configuration
│   │   └── utils/
│   │       ├── logger.py        # Logging
│   │       └── embed.py         # Embeddings
│   ├── main.py                  # Backend entry point
│   ├── test_pubmed.py          # Automated tests
│   ├── test_pubmed_cli.py      # Interactive CLI
│   └── .env.template           # Config template
│
├── frontend/                    # Streamlit UI
│   ├── app.py                  # Main application
│   └── requirements.txt        # Frontend dependencies
│
├── requirements.txt            # Unified dependencies
├── README.md                   # This file
└── ARCHITECTURE.md            # Detailed architecture docs
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **Ollama** - [Install Ollama](https://ollama.ai/)
3. **API Keys** (free):
   - [NCBI API Key](https://www.ncbi.nlm.nih.gov/account/)
   - [Google API Key](https://makersuite.google.com/app/apikey)

### Installation

#### 1. Install Ollama and Pull Model

```bash
# Install Ollama from https://ollama.ai/
# Then pull the model:
ollama pull gemma2:2b
```

#### 2. Clone Repository

```bash
git clone <repository-url>
cd MedToolAgent
```

#### 3. Install Dependencies

**Option A: Install everything (recommended)**
```bash
pip install -r requirements.txt
```

**Option B: Install separately**
```bash
# Backend only
cd backend
pip install -r requirements.txt

# Frontend only
cd frontend
pip install -r requirements.txt
```

#### 4. Configure Environment

```bash
cd backend
copy .env.template .env
```

Edit `.env` and add your API keys:
```env
# NCBI/PubMed API
NCBI_API_KEY=your_ncbi_api_key_here
NCBI_EMAIL=your_email@example.com

# Google AI (for embeddings)
GOOGLE_API_KEY=your_google_api_key_here

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
AGENT_MODEL=gemma2:2b
SAFETY_MODEL=gemma2:2b
```

### Running the Application

#### Start Backend Server

```bash
cd backend
python main.py
```

Server runs on `http://localhost:8000`

#### Start Frontend (in new terminal)

```bash
cd frontend
streamlit run app.py
```

UI opens at `http://localhost:8501`

## 💡 Usage Examples

### Via Web Interface

1. Open `http://localhost:8501` in your browser
2. Enter a medical query: *"What are the latest treatments for Type 2 diabetes?"*
3. Click **"Analyze & Respond"**
4. View AI response with safety verification
5. Check detailed analysis in sidebar

### Via API

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find recent research on COVID-19 vaccines",
    "thread_id": "session-123"
  }'
```

**Response:**
```json
{
  "status": "success",
  "generation": "Based on recent PubMed research...",
  "safety_report": "SAFE - Response is medically accurate",
  "is_valid": true,
  "final_output": "..."
}
```

### Via Python

```python
from src.tools.base import search_pubmed

# Search PubMed
result = search_pubmed.invoke({
    "query": "cancer immunotherapy",
    "num_articles": 15,
    "top_n": 5
})

print(result)
```

### Via Interactive CLI

```bash
cd backend
python test_pubmed_cli.py
```

Follow the prompts to search, view, and save articles.

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Ollama API endpoint | `http://localhost:11434` |
| `AGENT_MODEL` | Main LLM model | `gemma2:2b` |
| `SAFETY_MODEL` | Safety check model | `gemma2:2b` |
| `NCBI_API_KEY` | NCBI API key | Required |
| `NCBI_EMAIL` | Your email for NCBI | Required |
| `GOOGLE_API_KEY` | Google AI API key | Required |
| `LOG_LEVEL` | Logging level | `INFO` |

### Tool Configuration

Edit `backend/src/tools/base.py` to customize tool behavior:

```python
# Customize PubMed search defaults
result = search_pubmed.invoke({
    "query": "your query",
    "num_articles": 20,  # Fetch 20 articles
    "top_n": 5           # Return top 5
})
```

## 🧪 Testing

### Run Automated Tests

```bash
cd backend
python test_pubmed.py
```

### Run Interactive CLI

```bash
cd backend
python test_pubmed_cli.py
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Process query
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"query": "symptoms of diabetes"}'
```

## 📚 Available Tools

### 1. PubMed Article Fetcher (Enhanced)

**Function**: `search_pubmed(query, num_articles=10, top_n=3)`

**Features**:
- Searches PubMed via NCBI Entrez API
- Fetches complete article details
- Extracts full text from PMC when available
- Retrieves artifacts (tables, figures, supplementary materials)
- **Semantic ranking** using Google Gemini embeddings + FAISS
- Returns top N most relevant articles

**Example**:
```python
result = search_pubmed.invoke({
    "query": "diabetes treatment guidelines",
    "num_articles": 15,
    "top_n": 5
})
```

### 2. EHR Data Fetcher (Mock)

**Function**: `fetch_ehr_data(patient_id)`

**Retrieves electronic health records (mock implementation for demo).**

### 3. Clinical Guidelines RAG (Mock)

**Function**: `rag_clinical_data(query)`

**Queries local clinical knowledge base (mock implementation for demo).**

## 🛠️ Development

### Adding New Tools

1. **Define tool in `backend/src/tools/base.py`:**

```python
from langchain_core.tools import tool

@tool
def my_new_tool(param: str) -> str:
    """Tool description for the LLM."""
    # Implementation
    return "result"
```

2. **Add to tools list:**

```python
agent_tools = [search_pubmed, fetch_ehr_data, rag_clinical_data, my_new_tool]
```

3. **Update tool prompt in `backend/src/agent/nodes.py`:**

```python
TOOL_PROMPT = """...
4. my_new_tool(param: str) - Description
..."""
```

4. **Add handling in `llm_agent` function:**

```python
elif tool_name == "my_new_tool":
    tool_result = my_new_tool.invoke({"param": tool_arg})
```

### Modifying the Workflow

Edit `backend/src/agent/graph.py` to change the LangGraph workflow:

```python
# Add new node
workflow.add_node("my_node", my_node_function)

# Add edge
workflow.add_edge("existing_node", "my_node")
```

### Custom Embeddings

To use a different embedding model, edit `backend/src/utils/embed.py`:

```python
def get_embedding(text: str, model: str = "your-model-here"):
    # Custom implementation
    pass
```

## 🐛 Troubleshooting

### Common Issues

**"model not found" error**
```bash
# Ensure Ollama is running
ollama serve

# Pull the model
ollama pull gemma2:2b
```

**"NCBI API key not found"**
- Add `NCBI_API_KEY` to `backend/.env`
- Get key from https://www.ncbi.nlm.nih.gov/account/

**"Error generating embedding"**
- Add `GOOGLE_API_KEY` to `backend/.env`
- Get key from https://makersuite.google.com/app/apikey

**"Connection refused" to Ollama**
- Check Ollama is running: `ollama serve`
- Verify `OLLAMA_BASE_URL` in `.env`

**"No full text available" for articles**
- Normal! Not all articles have full text in PMC
- Abstract and metadata are still available

**Frontend can't connect to backend**
- Ensure backend is running on port 8000
- Check API URL in Streamlit sidebar settings

## 🔒 Security & Privacy

### API Key Management
- All keys stored in `.env` (gitignored)
- Never commit credentials to version control
- Use environment variables in production

### Medical Data
- No PHI (Protected Health Information) stored
- PubMed data is public domain
- EHR tool is mock implementation only
- Conversation state in memory only (not persisted)

### Rate Limiting
- NCBI API: 10 req/sec with key, 3 req/sec without
- Automatic delays implemented in code
- Google Gemini: Per API key limits

## 📊 Performance

### Typical Response Times
- Simple query (no tools): 2-5 seconds
- PubMed search (10 articles): 15-30 seconds
- With safety check: +2-3 seconds
- Recovery retry: +5-10 seconds

### Optimization Tips
1. Reduce `num_articles` for faster searches
2. Use caching for repeated queries
3. Run Ollama on GPU for faster inference
4. Consider async processing for large batches

## 🚢 Deployment

### Docker (Recommended)

```dockerfile
# Example Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Start backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Checklist
- [ ] Set up environment variables
- [ ] Configure reverse proxy (Nginx)
- [ ] Enable HTTPS
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure logging
- [ ] Set up database for persistent checkpointing
- [ ] Implement caching (Redis)
- [ ] Set up CI/CD pipeline

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/MedToolAgent.git
cd MedToolAgent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest black flake8 mypy

# Run tests
cd backend
python test_pubmed.py
```

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) for agent orchestration
- Powered by [Ollama](https://ollama.ai/) for local LLM inference
- UI with [Streamlit](https://streamlit.io/)
- Medical data from [NCBI PubMed](https://pubmed.ncbi.nlm.nih.gov/)
- Embeddings by [Google Gemini](https://ai.google.dev/)
- Vector search with [FAISS](https://github.com/facebookresearch/faiss)

## 📞 Support

- **Documentation**: Check [ARCHITECTURE.md](ARCHITECTURE.md) and other docs
- **Issues**: Open an issue on GitHub
- **Questions**: Start a discussion on GitHub Discussions

## 🗺️ Roadmap

### Current Version (v1.0)
- ✅ Multi-agent workflow
- ✅ PubMed integration with semantic ranking
- ✅ Safety verification
- ✅ Recovery mechanism
- ✅ Streamlit UI
- ✅ Conditional Tool Calling
- ✅ Iterative Refinement Loop

### Planned Features
- [ ] Enhanced RAG with local vector database
- [ ] Multi-modal support (medical imaging)
- [ ] Citation management and bibliography generation
- [ ] Export options (PDF, CSV)
- [ ] Advanced filtering (journal, publication type, date)
- [ ] Multi-user collaboration
- [ ] Analytics dashboard
- [ ] Mobile app

### Technical Improvements
- [ ] Full async/await architecture
- [ ] Multi-layer caching
- [ ] Persistent database storage
- [ ] Comprehensive monitoring
- [ ] 80%+ test coverage
- [ ] OpenAPI documentation

---

**Made with ❤️ for the medical AI community**

**Star ⭐ this repo if you find it useful!**
