# Deployment

Production deployment guide for the Genomic.go Platform on Google Kubernetes Engine (GKE).

---

## Infrastructure Overview

| Component | Technology | Notes |
|-----------|-----------|-------|
| Container orchestration | Google Kubernetes Engine (GKE) | |
| Container registry | Google Container Registry (GCR) | |
| Vector database | Qdrant (self-hosted on GKE) | |
| Event streaming | Apache Kafka (self-hosted or managed) | |
| Relational DB | Cloud SQL (PostgreSQL) | |
| Document DB | MongoDB Atlas | |
| Secrets management | GCP Secret Manager | |
| Monitoring | Prometheus + Grafana | |
| Load balancing | Google Cloud Load Balancer | TLS termination |

**Estimated monthly cost at full production scale:** ~$16,000

---

## Prerequisites

- GCP project with billing enabled
- `gcloud` CLI configured
- `kubectl` configured for your GKE cluster
- `docker` installed
- `helm` for Kafka / monitoring chart deployment

---

## Docker Setup

### Building the Image

```dockerfile
# Example Dockerfile (create at repo root)
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and tag
docker build -t gcr.io/<PROJECT_ID>/genomic-platform:latest .

# Push to GCR
docker push gcr.io/<PROJECT_ID>/genomic-platform:latest
```

---

## GKE Cluster Setup

```bash
# Create cluster with 3 node pools
gcloud container clusters create genomic-platform \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n2-standard-8

# Separate node pool for agent workloads
gcloud container node-pools create agent-pool \
  --cluster genomic-platform \
  --zone us-central1-a \
  --num-nodes 5 \
  --machine-type n2-standard-16 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 20

# Node pool for database workloads
gcloud container node-pools create database-pool \
  --cluster genomic-platform \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n2-highmem-8
```

---

## Kubernetes Manifests

### Namespace Setup

```yaml
# k8s/namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: genomic-api
---
apiVersion: v1
kind: Namespace
metadata:
  name: genomic-agents
---
apiVersion: v1
kind: Namespace
metadata:
  name: genomic-data
```

### API Gateway Deployment

```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: genomic-api
  namespace: genomic-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: genomic-api
  template:
    metadata:
      labels:
        app: genomic-api
    spec:
      containers:
      - name: api
        image: gcr.io/<PROJECT_ID>/genomic-platform:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: genomic-secrets
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
---
apiVersion: v1
kind: Service
metadata:
  name: genomic-api-svc
  namespace: genomic-api
spec:
  selector:
    app: genomic-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Horizontal Pod Autoscaler

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: genomic-api-hpa
  namespace: genomic-api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: genomic-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Secrets Management

Store all API keys and credentials in GCP Secret Manager, then sync to Kubernetes Secrets:

```bash
# Store secrets in GCP Secret Manager
gcloud secrets create anthropic-api-key --data-file=- <<< "sk-ant-..."
gcloud secrets create openai-api-key --data-file=- <<< "sk-proj-..."
gcloud secrets create ethereum-private-key --data-file=- <<< "0x..."

# Sync to Kubernetes Secret (or use External Secrets Operator)
kubectl create secret generic genomic-secrets \
  --from-literal=ANTHROPIC_API_KEY=$(gcloud secrets versions access latest --secret=anthropic-api-key) \
  --from-literal=OPENAI_API_KEY=$(gcloud secrets versions access latest --secret=openai-api-key) \
  --namespace genomic-api
```

---

## Qdrant Deployment

```bash
# Deploy Qdrant via Helm on the database node pool
helm repo add qdrant https://qdrant.github.io/qdrant-helm
helm install qdrant qdrant/qdrant \
  --namespace genomic-data \
  --set persistence.size=500Gi \
  --set nodeSelector."cloud.google.com/gke-nodepool"=database-pool
```

Initialize the compound library after Qdrant is healthy:

```bash
kubectl run init-compounds \
  --image=gcr.io/<PROJECT_ID>/genomic-platform:latest \
  --namespace=genomic-data \
  --restart=Never \
  -- python -m src.compound_library.init_compound_library
```

---

## Kafka Deployment

```bash
# Deploy Kafka + Zookeeper via Bitnami Helm chart
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install kafka bitnami/kafka \
  --namespace genomic-data \
  --set replicaCount=3 \
  --set persistence.size=100Gi
```

Create required topics:

```bash
kubectl exec -it kafka-0 -n genomic-data -- \
  kafka-topics.sh --create \
    --bootstrap-server localhost:9092 \
    --topic trial-allocations \
    --partitions 6 \
    --replication-factor 3

# Repeat for trial-alerts and adverse-events
```

---

## Monitoring

### Prometheus + Grafana

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install kube-prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### Key Metrics to Monitor

| Metric | Alert threshold |
|--------|----------------|
| API p99 latency | > 2 seconds |
| Qdrant query time | > 500ms |
| Kafka consumer lag | > 1000 messages |
| Agent task failure rate | > 5% |
| AE rate (per trial) | Configured threshold (default 15%) |

---

## CI/CD Pipeline

### Recommended Flow

```
Push to feature branch
  → Lint + test (GitHub Actions)
  → Security scan (bandit, safety)
  → Code review

Merge to develop
  → Build Docker image
  → Push to GCR
  → Deploy to staging (GKE staging cluster)
  → Integration tests

Merge to main (release)
  → Build release image (tagged version)
  → Deploy to production GKE
  → Smoke tests
  → Notify team
```

---

## Disaster Recovery

| Metric | Target |
|--------|--------|
| RTO (Recovery Time Objective) | 1 hour |
| RPO (Recovery Point Objective) | 15 minutes |

### Backup Strategy

```bash
# Qdrant snapshot (run daily via CronJob)
curl -X POST http://qdrant:6333/collections/compound_library/snapshots

# Upload snapshot to GCS
gsutil cp /qdrant/snapshots/*.snapshot gs://<BACKUP_BUCKET>/qdrant/

# PostgreSQL: Cloud SQL automated backups (daily, 7-day retention)
# MongoDB Atlas: Continuous backup enabled
```

### Restore Procedure

1. Restore Qdrant snapshot from GCS
2. Restore PostgreSQL from Cloud SQL backup
3. Restart all Kubernetes deployments
4. Verify health endpoints
5. Run smoke tests

---

## Health Checks

Verify the platform is running:

```bash
# API Gateway
curl https://api.genomic.agicorp.network/health

# Qdrant
curl http://qdrant.genomic-data.svc.cluster.local:6333/healthz

# Kafka (from within cluster)
kubectl exec -it kafka-0 -n genomic-data -- \
  kafka-topics.sh --list --bootstrap-server localhost:9092
```

---

_Back to: [Home](Home.md) | [Configuration](Configuration.md)_
