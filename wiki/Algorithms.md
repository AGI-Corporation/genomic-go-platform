# Algorithms

This page documents the key scientific and ML algorithms used in the Genomic.go Platform.

---

## 1. Thompson Sampling (Adaptive Trial Randomization)

**Used in:** `AdaptiveTrialDesign.allocate_patient()`  
**File:** `src/clinical_trials/realtime_optimizer.py`

### Background

Thompson sampling is a Bayesian algorithm for the multi-armed bandit problem. In clinical trials it enables **response-adaptive randomization** — arms with higher observed success rates receive more patient allocations over time.

### Algorithm

Each treatment arm `k` maintains a Beta distribution `Beta(α_k, β_k)`:
- `α_k` = number of successes on arm k + 1 (prior)
- `β_k` = number of failures on arm k + 1 (prior)

At each patient allocation:
```
For each arm k:
    sample_k ~ Beta(α_k, β_k)

allocated_arm = argmax(sample_k)
```

After observing outcome for arm k:
```
If success:   α_k += 1
If failure:   β_k += 1
```

### Properties

- Starts with uniform allocation (flat Beta priors)
- Naturally concentrates allocation toward superior arms
- Maintains some exploration of all arms (no arm is permanently excluded)
- Conjugate updates: O(1) per outcome

---

## 2. O'Brien-Fleming Stopping Boundaries

**Used in:** `AdaptiveTrialDesign.check_stopping_rules()`  
**File:** `src/clinical_trials/realtime_optimizer.py`

### Background

Group sequential methods allow a clinical trial to stop early based on interim analyses without inflating the Type I error rate.

### Stopping Rules Implemented

**Futility boundary:**
- Stop enrollment if all arms have observed success rate < 20%
- Prevents continued exposure to an ineffective treatment

**Superiority boundary:**
- Calculate Z-statistic comparing the best arm to the worst arm
- Stop if Z > 4.0 (highly conservative, controlling Type I error)

**Information fraction:**
- Can stop at ≥50% information if boundaries are crossed
- Information fraction = enrolled patients / planned sample size

### Decision Logic

```
For each arm:
    rate = successes / (successes + failures)

If max(rate) < 0.20:
    stop → "futility"

z = (rate_best - rate_worst) / sqrt(pooled_se)
If z > 4.0:
    stop → "superiority"

Else:
    continue enrollment
```

---

## 3. Sequential Probability Ratio Test (SPRT)

**Used in:** `SafetyMonitoringSystem`  
**File:** `src/clinical_trials/realtime_optimizer.py`

### Background

SPRT is a sequential hypothesis test that makes a decision as soon as enough evidence accumulates, rather than waiting for a fixed sample size. It minimizes expected sample size while controlling both Type I (α) and Type II (β) error rates.

### Application

Continuously tests whether the 7-day rolling adverse event (AE) rate has exceeded the pre-specified safety threshold (default 15%).

### Algorithm

```
H0: AE rate ≤ p0 (acceptable)
H1: AE rate > p1 (unacceptable)

At each new event:
    Update rolling 7-day AE count and total observations
    Compute rolling_rate = AE_count_7d / observations_7d

If rolling_rate > safety_threshold:
    Publish alert to Kafka topic: "trial-alerts"
    alert_type = "safety_threshold_exceeded"
```

---

## 4. Vector Embedding + Approximate Nearest Neighbor Search

**Used in:** `CompoundSearcher.search()`, `RealTimePatientMatcher.find_matching_trials()`  
**Files:** `src/compound_library/compound_searcher.py`, `src/clinical_trials/realtime_optimizer.py`

### Embedding Models

| Use Case | Model | Dimensions |
|----------|-------|-----------|
| Compound search | `all-MiniLM-L6-v2` | 384 |
| Patient-trial matching | Custom model | 768 |

### HNSW Index

Qdrant uses Hierarchical Navigable Small World (HNSW) graphs for approximate nearest neighbor (ANN) search.

**Index parameters:**
```
m = 16               # Max edges per node
ef_construct = 100   # Candidate pool during construction
```

**Search complexity:** O(log N) average case

**Search process:**
```
1. Encode query text → dense vector (384 or 768 dims)
2. Enter HNSW graph at highest layer
3. Greedily navigate toward query vector
4. Expand candidate set at each layer
5. Return top-k by cosine similarity
6. Apply scalar quantization (INT8) for memory efficiency
```

### Filtering

Post-ANN filtering applies hard eligibility constraints:
- Range filters on `molecular_weight`
- Keyword match on `therapeutic_area`, `clinical_phase`, `target_protein`
- Set intersection/disjunction for genomic markers

---

## 5. XGBoost Endpoint Prediction

**Used in:** `EndpointPredictor.predict()`  
**File:** `src/clinical_trials/realtime_optimizer.py`

### Model Overview

Gradient-boosted decision tree (GBDT) model trained on historical clinical trial interim data to predict final endpoint outcomes.

### Inference Pipeline

```
1. Load pre-trained XGBoost model from disk
2. Engineer features from interim trial data:
   - Observed response rates per arm
   - Enrollment completion fraction
   - Time-to-event metrics
   - Biomarker distributions
3. Run model.predict_proba()  → base probability
4. Bootstrap confidence intervals:
   For i in range(100):
       sample = resample(interim_data)
       boot_pred[i] = model.predict_proba(sample)
   CI = percentile(boot_pred, [2.5, 97.5])
5. Extrapolate to final endpoint:
   extrapolated = base_prob * information_fraction_correction
```

**Output:**
```python
{
    "probability": 0.742,
    "ci_lower": 0.681,
    "ci_upper": 0.803,
    "extrapolated_endpoint": 0.75
}
```

---

## 6. Bayesian Beta-Binomial Posterior

**Used in:** Throughout `AdaptiveTrialDesign`  
**File:** `src/clinical_trials/realtime_optimizer.py`

### Model

For each arm k:
- **Prior:** `Beta(1, 1)` (uniform)
- **Likelihood:** `Binomial(n_k, θ_k)`
- **Posterior:** `Beta(α_k + successes_k, β_k + failures_k)`

The posterior mean is used as the estimated success probability:
```
θ̂_k = α_k / (α_k + β_k)
```

The posterior distribution quantifies uncertainty about each arm's true success rate and drives Thompson sampling.

---

## 7. Multi-Node Redundancy (AlphaFold3)

**Used in:** `NANDAProtocolCoordinator.submit_task()`  
**File:** `src/integrations/alphafold3_nanda_integration.py`

### Purpose

Protein structure prediction can take minutes per sequence. Deploying to multiple nodes in parallel guards against node failure and reduces average wait time.

### Algorithm

```
Input: sequence, redundancy_factor=2

1. Score all registered nodes by current load:
   load_score = active_tasks / max_capacity

2. Select top-N least-loaded nodes (N = redundancy_factor)

3. Submit task to each selected node in parallel:
   asyncio.gather(*[dispatch(node, task) for node in selected_nodes])

4. Background health monitor (every 10s, timeout 30s):
   If node heartbeat fails:
       _handle_node_failure(node_id)
       Reassign in-flight tasks to healthy nodes

5. Return first successful prediction result.
   Cancel remaining submissions.
```

---

## 8. Kalibr Intelligent LLM Routing

**Used in:** All LLM inference calls  
**Integrated via:** `kalibr` Python package

### Routing Strategy

Kalibr dynamically selects the optimal LLM provider based on:

| Factor | Weight |
|--------|--------|
| Task complexity | High |
| Token cost | High |
| Provider latency | Medium |
| Provider availability | Medium |

**Model pool:**
- `gpt-4o` — complex reasoning, research summarization
- `gpt-4o-mini` — fast, low-cost tasks
- `claude-sonnet-4` — long-context, nuanced analysis
- `gemini-2.5-pro` — multimodal or scientific content

**Result:** Up to 90% reduction in LLM spend vs. always using GPT-4o.

---

_Next: [Configuration](Configuration.md) | [Security](Security.md)_
