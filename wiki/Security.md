# Security

Security architecture, authentication model, compliance posture, and best practices for the Genomic.go Platform.

---

## Security Model Overview

Genomic.go follows a **Zero-Trust security architecture**: no component is implicitly trusted, every request is authenticated and authorized regardless of network location.

### Core Principles

1. **Verify explicitly** — Authenticate and authorize every request using identity, location, and risk signals
2. **Least privilege** — Each agent/service has only the minimum permissions needed
3. **Assume breach** — Design for detection and containment, not just prevention

---

## Authentication

### User Authentication

| Mechanism | Details |
|-----------|---------|
| Protocol | OAuth 2.0 Authorization Code flow |
| Token type | JWT (JSON Web Token), Bearer scheme |
| Signing | RS256 (RSA + SHA-256) |
| Expiry | Short-lived access tokens (e.g. 15 minutes) + refresh tokens |

All API requests must include:
```
Authorization: Bearer <jwt_token>
```

### Service-to-Service Authentication

| Mechanism | Details |
|-----------|---------|
| Protocol | Mutual TLS (mTLS) |
| TLS version | 1.3 minimum |
| Certificate rotation | Automated |

NANDA agents authenticate with the Anthropic API using `ANTHROPIC_API_KEY` and with the NANDA registry using the configured domain.

### Qdrant Cloud Authentication

Qdrant Cloud deployments require `QDRANT_API_KEY` passed via HTTP header.

---

## Authorization

### Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| `researcher` | Read compound library, submit workflows |
| `clinician` | Manage trial allocations, view patient matches |
| `admin` | Full platform access, user management |
| `service` | Internal service-to-service calls only |

RBAC rules are enforced at the API Gateway before requests reach downstream services.

---

## Encryption

| Layer | Mechanism |
|-------|-----------|
| Encryption at rest | AES-256 (Qdrant, PostgreSQL, MongoDB) |
| Encryption in transit | TLS 1.3 (external), mTLS (internal) |
| Ethereum wallet | Private key stored in secrets manager, never in code |

---

## Sensitive Data Handling

### HIPAA Compliance

Patient data processed by the clinical trials module is subject to HIPAA requirements:
- Patient profiles are stored only in HIPAA-compliant zones
- All access to patient records is audit-logged
- PHI is not included in Kafka messages beyond anonymized IDs
- Data isolation: clinical data isolated from other workloads at the Kubernetes namespace level

### Genomic Data

- Genomic variants are treated as sensitive PII/PHI
- Embeddings derived from patient data are not reversible (one-way transformation)
- Qdrant collections storing patient embeddings are access-controlled by role

### API Keys and Secrets

**Required practices:**
- All secrets loaded from environment variables or a secrets manager (never hardcoded)
- `.env` file excluded from version control via `.gitignore`
- Production secrets managed via GCP Secret Manager or Kubernetes Secrets
- Ethereum `PRIVATE_KEY` never committed to source control — use a hardware wallet or KMS in production

---

## Network Security

### Inbound Traffic

```
Internet → Cloud Load Balancer (TLS termination)
         → API Gateway (JWT validation, rate limiting)
         → Internal services (mTLS)
```

### Internal Traffic

- Kubernetes NetworkPolicy restricts pod-to-pod communication
- Each service group (agents, databases, API) is isolated in its own namespace
- Qdrant and Kafka are not exposed outside the cluster

### Rate Limiting

- Per-user and per-endpoint request limits enforced at the API Gateway
- Burst protection against credential stuffing and scraping attacks

---

## Audit Logging

All data access and mutation events are logged with:
- Timestamp
- User identity (subject from JWT)
- Resource accessed
- Action taken
- Source IP

Logs are shipped to a centralized SIEM for monitoring and alerting.

---

## Vulnerability Management

### Dependency Scanning

The development toolchain includes:
```bash
safety check          # Check requirements.txt for known CVEs
bandit -r src/        # Static analysis for Python security issues
```

Run both before every release:
```bash
pip install safety bandit
safety check
bandit -r src/ -ll
```

### Code Analysis

- `bandit` flags dangerous patterns: `subprocess` misuse, hardcoded credentials, weak cryptography
- `mypy` strict typing reduces class of runtime errors

---

## Compliance

| Standard | Status | Notes |
|----------|--------|-------|
| HIPAA | Designed for compliance | Patient data isolation, audit logs, encryption |
| GDPR | Designed for compliance | Data minimization, right to erasure workflow |
| SOC 2 Type II | Targeted | Audit logging, access controls, availability SLAs |
| 21 CFR Part 11 | Partial | Audit trails for clinical trial records |

---

## Security Best Practices for Developers

1. **Never print or log API keys, patient IDs, or genomic data**
2. **Always use parameterized queries** — no string interpolation in database calls
3. **Validate all external input** before processing (trial IDs, compound IDs, patient data)
4. **Use `asyncio.gather(..., return_exceptions=True)`** — never silently swallow exceptions from security-critical paths
5. **Rotate API keys periodically** and revoke compromised keys immediately
6. **Review Kafka message schemas** — ensure no PHI leaks into `trial-allocations` or `trial-alerts` topics
7. **Keep dependencies up to date** — run `safety check` and `pip list --outdated` regularly

---

## Reporting Security Vulnerabilities

See [SECURITY.md](../SECURITY.md) for the responsible disclosure policy.

Do **not** file public GitHub issues for security vulnerabilities. Contact the security team directly via the email listed in `SECURITY.md`.

---

_Next: [Development Guide](Development-Guide.md) | [Deployment](Deployment.md)_
