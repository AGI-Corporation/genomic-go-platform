# Contributing to Genomic.go Platform

Thank you for your interest in contributing to the Genomic.go Platform! We welcome contributions from the scientific and developer communities to help advance this cutting-edge research platform.

## 🌟 Code of Conduct

By participating in this project, you agree to maintain a professional, respectful, and inclusive environment. We are committed to making participation in this project a harassment-free experience for everyone.

### Our Standards

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

## 📋 How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear, descriptive title
- Detailed steps to reproduce the issue
- Expected vs. actual behavior
- Screenshots (if applicable)
- Environment details (OS, browser, version, etc.)
- Relevant log outputs or error messages

### Suggesting Enhancements

We welcome feature suggestions! Please:
- Check existing issues to avoid duplicates
- Provide a clear use case for the enhancement
- Explain how it benefits the scientific community
- Consider implementation complexity
- Include mockups or examples if applicable

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow our coding standards** (see below)
3. **Write clear commit messages** following conventional commits
4. **Add tests** for new functionality
5. **Update documentation** as needed
6. **Ensure CI/CD passes** before requesting review

## 🔬 Development Guidelines

### Branch Naming Convention

Use descriptive branch names with prefixes:
- `feature/` - New features (e.g., `feature/alphafold-integration`)
- `fix/` - Bug fixes (e.g., `fix/agent-communication-bug`)
- `docs/` - Documentation updates (e.g., `docs/api-reference`)
- `refactor/` - Code refactoring (e.g., `refactor/swarm-architecture`)
- `test/` - Test additions/updates (e.g., `test/molecular-dynamics`)
- `chore/` - Maintenance tasks (e.g., `chore/dependency-update`)

### Commit Message Format

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style/formatting
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks
- `perf`: Performance improvements

**Example:**
```
feat(agent-swarm): Add OML fingerprinting capability

Implemented Organic Machine Learning fingerprinting for enhanced 
pattern recognition in biological data. This enables the Sentient 
Enclave to perform cross-domain knowledge synthesis.

Closes #123
```

### Coding Standards

#### TypeScript/JavaScript
- Use TypeScript for all new code
- Follow ESLint and Prettier configurations
- Use meaningful variable and function names
- Add JSDoc comments for public APIs
- Maximum line length: 100 characters
- Use async/await over callbacks
- Prefer functional programming patterns

#### Python
- Follow PEP 8 style guide
- Use type hints for function signatures
- Add docstrings (Google style)
- Use Black for code formatting
- Maximum line length: 88 characters
- Use virtual environments
- Prefer context managers for resource handling

#### React Components
- Use functional components with hooks
- PropTypes or TypeScript interfaces required
- One component per file
- Use CSS modules or styled-components
- Follow atomic design principles
- Ensure accessibility (WCAG 2.1 AA)

### Testing Requirements

- **Unit Tests**: Required for all new functions/methods
- **Integration Tests**: Required for API endpoints and agent interactions
- **E2E Tests**: Required for critical user workflows
- **Coverage**: Maintain >80% code coverage
- **Performance Tests**: Required for computationally intensive features

**Testing Frameworks:**
- TypeScript/JavaScript: Jest, React Testing Library
- Python: pytest, unittest
- E2E: Playwright or Cypress

### Documentation Standards

#### Code Documentation
- Add inline comments for complex logic
- Use JSDoc/docstrings for all public APIs
- Include usage examples in documentation
- Document edge cases and error handling

#### README Updates
- Keep README.md current with new features
- Update installation instructions if dependencies change
- Add new configuration options to documentation
- Update architecture diagrams if structure changes

#### API Documentation
- Use OpenAPI/Swagger for REST APIs
- Document all endpoints, parameters, and responses
- Include example requests and responses
- Version API documentation

## 🧪 Scientific Contributions

### Agent Swarm Development

When contributing new agent swarms or enhancements:
- Clearly define the agent's domain expertise
- Document the scientific rationale
- Provide validation against known benchmarks
- Include references to relevant research papers
- Ensure interoperability with Bio-MCP protocol

### Research Tool Integration

For new research tool integrations:
- Provide scientific validation of the tool
- Document input/output formats
- Include example workflows
- Ensure compatibility with existing pipelines
- Add appropriate error handling for edge cases

### Algorithm Contributions

When contributing algorithms:
- Include mathematical formulation
- Provide complexity analysis
- Compare against baseline methods
- Include validation datasets
- Document hyperparameters and tuning strategies

## 📦 Project Structure

```
genomic-go-platform/
├── .github/                 # GitHub workflows and templates
├── docs/                    # Documentation
├── src/                     # Source code
│   ├── api/                 # REST API endpoints
│   ├── clinical_trials/     # Trial optimization engine
│   ├── compound_library/    # Drug design and search
│   ├── integrations/        # Mistral and Bio-MCP integrations
│   ├── interface/           # Streamlit workbench
│   ├── research_framework/  # Swarm and Knowledge Graph
│   └── schemas/             # Pydantic data models
├── tests/                   # Test suites
├── Dockerfile               # Production containerization
└── requirements.txt         # Project dependencies
```

## 🔄 Development Workflow

### 1. Set Up Development Environment

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/genomic-go-platform.git
cd genomic-go-platform

# Add upstream remote
git remote add upstream https://github.com/AGI-Corporation/genomic-go-platform.git

# Install dependencies
npm install
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install
```

### 2. Create Feature Branch

```bash
# Update your fork
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 3. Make Changes

- Write code following our standards
- Add tests for new functionality
- Run tests locally: `npm test` and `pytest`
- Run linters: `npm run lint` and `flake8`
- Update documentation

### 4. Commit Changes

```bash
# Stage changes
git add .

# Commit with conventional commit message
git commit -m "feat(scope): description"

# Push to your fork
git push origin feature/your-feature-name
```

### 5. Create Pull Request

- Go to the original repository on GitHub
- Click "New Pull Request"
- Select your fork and branch
- Fill in the PR template completely
- Request review from maintainers

### 6. Address Review Feedback

- Respond to all comments
- Make requested changes
- Push updates to the same branch
- Request re-review when ready

## 🚀 Release Process

Releases are managed by maintainers using semantic versioning:
- **Major** (x.0.0): Breaking changes
- **Minor** (0.x.0): New features (backward compatible)
- **Patch** (0.0.x): Bug fixes

## 📜 License

By contributing to Genomic.go Platform, you agree that your contributions will be licensed under the MIT License.

## 🤝 Community

### Getting Help

- **GitHub Discussions**: Ask questions and share ideas
- **Slack Channel**: Join our developer community
- **Office Hours**: Monthly virtual office hours with maintainers
- **Documentation**: Check our comprehensive docs first

### Maintainers

Current maintainers:
- **@AGI-Corporation** - Project Lead
- See [MAINTAINERS.md](MAINTAINERS.md) for full list

### Recognition

Contributors are recognized through:
- Attribution in release notes
- Contributor badge on README
- IP-NFT framework for significant contributions
- $lab token rewards for substantial contributions

## 📧 Contact

For questions about contributing:
- **Email**: developers@agicorp.ai
- **GitHub**: [@AGI-Corporation](https://github.com/AGI-Corporation)
- **Website**: [https://agicorp.ai](https://agicorp.ai)

---

Thank you for helping advance scientific research through open collaboration! Your contributions directly impact researchers worldwide working to solve critical challenges in genomics, drug discovery, and human health.

**© 2025 AGI Corporation. All rights reserved.**
