# Getting Started with Genomic.go Platform

Welcome to the Genomic.go Platform! This guide will help you set up and start using the platform for your research needs.

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip package manager
- Git
- Mistral API Key (`MISTRAL_API_KEY`)
- Docker (optional, for containerized deployment)

### Installation

```bash
# Clone the repository
git clone https://github.com/AGI-Corporation/genomic-go-platform.git
cd genomic-go-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Configuration

1. **API Keys**: Add your API keys to the `.env` file:
   ```
   OPENAI_API_KEY=your_key_here
   ANTHROPIC_API_KEY=your_key_here
   ```

2. **Database**: Configure your database connection (PostgreSQL recommended)

3. **Agent Framework**: Choose your preferred framework (Kalibr, CrewAI, or LangGraph)

### Running the Platform

```bash
# Start the interactive Streamlit workbench
streamlit run src/interface/app.py

# Run the API server
uvicorn src.api.main:app --reload

# Execute a discovery pipeline via CLI
python3 src/research_framework/cli.py "Cystic Fibrosis"
```

## 📚 Core Concepts

### Agent Swarms
The platform uses AI agent swarms for distributed research tasks:
- **Kalibr Router**: Intelligent task routing and orchestration
- **CrewAI**: Collaborative agent teams for complex workflows
- **LangGraph**: State machine-based agent coordination

### Research Domains

1. **Genomics**: DNA sequencing, variant analysis, pathway discovery
2. **Proteomics**: Protein structure prediction, interaction mapping
3. **Drug Discovery**: Compound screening, target identification, clinical trial analysis

### DeSci Integration

- **IP-NFT**: Tokenize and protect your research IP
- **Transparent Tracking**: All research steps recorded on-chain
- **Fair Attribution**: Automatic contributor recognition
- **Open Science**: Share findings while protecting intellectual property

## 🔬 Your First Research Project

### Example: Mistral-Powered Discovery

```python
from src.research_framework.discovery_tool import GenomicDiscoveryTool

# Initialize the tool
tool = GenomicDiscoveryTool()

# Run the end-to-end R&D pipeline
report = await tool.accelerate_research("Alzheimer's Disease")

# View the AI-generated evaluation
print(report['evaluation']['scientific_accuracy'])
```

## 🎯 Next Steps

1. **Read the Full Documentation**: Check out the [docs](./README.md) folder
2. **Explore Examples**: See `examples/` directory for sample projects
3. **Join the Community**: Connect with other researchers
4. **Contribute**: See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines

## 🆘 Need Help?

- **Documentation**: Full docs at `/docs`
- **Issues**: Report bugs via [GitHub Issues](https://github.com/AGI-Corporation/genomic-go-platform/issues)
- **Community**: Join our Discord/Slack
- **Email**: research@agicorp.eth

## 📖 Additional Resources

- [Architecture Overview](./architecture.md)
- [API Reference](./api-reference.md)
- [Agent Configuration](./agent-config.md)
- [DeSci Integration Guide](./desci-guide.md)
- [Security Best Practices](../SECURITY.md)

---

**Ready to accelerate your research? Let's get started! 🚀**

### 🤖 Multimodal Research (Vision & Voice)
1. **Analyze Imagery**: Use the `MistralGenomicAdapter` to interpret protein folds or microscope data.
2. **Audio Data**: Transcribe lab notes using `transcribe_research_notes` (Voxtral).

### ⚖️ Automated Quality Control
Every discovery is automatically graded by the **Mistral Judge** for scientific accuracy and clinical relevance, ensuring high-fidelity research outputs.
