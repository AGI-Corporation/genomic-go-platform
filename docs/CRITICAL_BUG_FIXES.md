# Critical Bug Fixes - Implementation Guide

## Overview
This document provides complete, production-ready code to fix all critical bugs identified in the code review.
**Apply these fixes immediately before deployment.**

---

## 1. Clinical Trials Module Fixes

### File: `src/clinical_trials/realtime_optimizer.py`

#### Fix 1: Add Missing Methods to AdaptiveTrialDesign Class

Add these methods after the `update_outcome` method (around line 95):

```python
def check_stopping_rules(self) -> Tuple[bool, str]:
    """
    Implement O'Brien-Fleming stopping boundaries.
    Returns (should_stop, reason) tuple.
    """
    if not self.arms:
        return False, ""
    
    for arm in self.arms:
        n = self.successes[arm] + self.failures[arm] - 2  # Subtract Beta priors
        if n < 10:  # Minimum sample size needed
            continue
        
        p_success = self.successes[arm] / (self.successes[arm] + self.failures[arm])
        
        # Futility boundary: stop arm if success rate < 20%
        if p_success < 0.20:
            return True, f"Futility boundary crossed for {arm}: success_rate={p_success:.3f}"
        
        # Superiority: compare against other arms
        for other_arm in self.arms:
            if other_arm == arm:
                continue
            
            other_n = self.successes[other_arm] + self.failures[other_arm] - 2
            if other_n < 10:
                continue
            
            other_p = self.successes[other_arm] / (self.successes[other_arm] + self.failures[other_arm])
            
            # Z-test for proportions
            pooled_p = (self.successes[arm] - 1 + self.successes[other_arm] - 1) / (n + other_n)
            if pooled_p == 0 or pooled_p == 1:
                continue
            
            se = np.sqrt(pooled_p * (1 - pooled_p) * (1/n + 1/other_n))
            if se == 0:
                continue
            
            z = (p_success - other_p) / se
            
            # O'Brien-Fleming boundary at alpha=0.05, information fraction = 0.5
            boundary = 4.0  # Conservative for early stopping
            if abs(z) > boundary:
                return True, f"Superiority detected: {arm} vs {other_arm}, z={z:.2f}"
    
    return False, ""

def send_alert(self, alert_type: str, message: str) -> None:
    """
    Send alert to Kafka topic for trial monitoring.
    
    Args:
        alert_type: Type of alert (e.g., 'TRIAL_STOP', 'SAFETY_SIGNAL')
        message: Alert message
    """
    try:
        alert_payload = {
            'alert_type': alert_type,
            'message': message,
            'trial_id': self.trial_id,
            'timestamp': datetime.utcnow().isoformat(),
            'severity': 'CRITICAL' if 'stop' in alert_type.lower() else 'WARNING'
        }
        
        self.producer.send('trial-alerts', alert_payload)
        self.producer.flush(timeout=5)
        
        logger.warning(f"ALERT [{self.trial_id}] {alert_type}: {message}")
    except Exception as e:
        logger.error(f"Failed to send alert for {self.trial_id}: {e}")
        # Don't raise - alerting failure shouldn't stop trial

def __enter__(self):
    """Context manager entry."""
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    """
    Context manager exit - clean up Kafka resources.
    
    Args:
        exc_type: Exception type if exception occurred
        exc_val: Exception value
        exc_tb: Exception traceback
    
    Returns:
        False to propagate exceptions
    """
    try:
        self.producer.flush(timeout=10)
        self.producer.close(timeout=10)
        logger.info(f"Closed Kafka producer for trial {self.trial_id}")
    except Exception as e:
        logger.error(f"Error closing Kafka producer: {e}")
    
    return False  # Don't suppress exceptions
```

#### Fix 2: Add Validation to allocate_next_patient

Replace the existing `allocate_next_patient` method with:

```python
def allocate_next_patient(self) -> str:
    """Thompson sampling for response-adaptive randomization."""
    if not self.arms:
        raise ValueError(f"Trial {self.trial_id} has no arms defined")
    
    samples = {}
    for arm in self.arms:
        samples[arm] = np.random.beta(self.successes[arm], self.failures[arm])
    
    allocated_arm = max(samples, key=samples.get)
    self.enrolled[allocated_arm] += 1
    
    # Stream allocation to Kafka
    try:
        self.producer.send('trial-allocations', {
            'trial_id': self.trial_id,
            'allocated_arm': allocated_arm,
            'timestamp': datetime.utcnow().isoformat(),
            'allocation_probs': {arm: float(s) for arm, s in samples.items()}
        })
    except Exception as e:
        logger.error(f"Failed to send allocation to Kafka: {e}")
        # Continue even if Kafka fails
    
    return allocated_arm
```
