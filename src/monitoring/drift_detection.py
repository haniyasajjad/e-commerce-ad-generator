"""
Model Drift Detection for Ad Creative Generator
Tracks:
1. Quality score drift
2. Response length drift
3. Keyword frequency drift
"""

import numpy as np
from collections import deque, Counter
from datetime import datetime
from prometheus_client import Gauge, Counter as PrometheusCounter
import mlflow

# Prometheus metrics for drift
quality_drift_score = Gauge(
    'model_quality_drift_score',
    'Statistical drift score for quality metric'
)

length_drift_score = Gauge(
    'model_length_drift_score',
    'Statistical drift score for response length'
)

keyword_drift_score = Gauge(
    'model_keyword_drift_score',
    'Drift in marketing keyword usage'
)

drift_alerts = PrometheusCounter(
    'model_drift_alerts_total',
    'Total drift alerts triggered',
    ['metric_type']
)

class DriftDetector:
    """
    Detects model drift using sliding window statistics
    Compares recent predictions against baseline
    """
    
    def __init__(self, window_size=100, baseline_window=500, drift_threshold=0.15):
        self.window_size = window_size
        self.baseline_window = baseline_window
        self.drift_threshold = drift_threshold
        
        # Sliding windows
        self.quality_scores = deque(maxlen=baseline_window)
        self.response_lengths = deque(maxlen=baseline_window)
        self.keyword_counts = deque(maxlen=baseline_window)
        
        # Baseline statistics (computed after baseline_window samples)
        self.baseline_quality_mean = None
        self.baseline_quality_std = None
        self.baseline_length_mean = None
        self.baseline_length_std = None
        self.baseline_keywords = None
        
        self.is_baseline_ready = False
        self.drift_detected = False
        
        # Marketing keywords to track
        self.tracked_keywords = [
            'sale', 'limited', 'now', 'free', 'best', 'save', 
            'grab', 'deal', 'discount', 'exclusive', 'new', 'today'
        ]
    
    def extract_keywords(self, text: str) -> Counter:
        """Extract marketing keyword frequencies"""
        text_lower = text.lower()
        counts = Counter()
        for keyword in self.tracked_keywords:
            counts[keyword] = text_lower.count(keyword)
        return counts
    
    def add_prediction(self, quality: float, response_text: str):
        """Add a new prediction for drift monitoring"""
        length = len(response_text.split())
        keywords = self.extract_keywords(response_text)
        
        self.quality_scores.append(quality)
        self.response_lengths.append(length)
        self.keyword_counts.append(keywords)
        
        # Establish baseline after enough samples
        if not self.is_baseline_ready and len(self.quality_scores) >= self.baseline_window:
            self._establish_baseline()
        
        # Check for drift if baseline is ready
        if self.is_baseline_ready:
            self._check_drift()
    
    def _establish_baseline(self):
        """Establish baseline statistics"""
        qualities = np.array(self.quality_scores)
        lengths = np.array(self.response_lengths)
        
        self.baseline_quality_mean = np.mean(qualities)
        self.baseline_quality_std = np.std(qualities)
        self.baseline_length_mean = np.mean(lengths)
        self.baseline_length_std = np.std(lengths)
        
        # Aggregate keyword frequencies
        self.baseline_keywords = Counter()
        for kw_count in self.keyword_counts:
            self.baseline_keywords.update(kw_count)
        
        self.is_baseline_ready = True
        print(f"✅ Drift detection baseline established:")
        print(f"   Quality: {self.baseline_quality_mean:.3f} ± {self.baseline_quality_std:.3f}")
        print(f"   Length: {self.baseline_length_mean:.1f} ± {self.baseline_length_std:.1f}")
        
        # Log to MLflow
        try:
            with mlflow.start_run(run_name=f"drift_baseline_{datetime.now().strftime('%Y%m%d')}"):
                mlflow.log_params({
                    "baseline_quality_mean": self.baseline_quality_mean,
                    "baseline_quality_std": self.baseline_quality_std,
                    "baseline_length_mean": self.baseline_length_mean,
                    "baseline_length_std": self.baseline_length_std,
                })
        except Exception as e:
            print(f"MLflow logging failed: {e}")
    
    def _check_drift(self):
        """Check for statistical drift in recent window"""
        # Get recent window
        recent_qualities = list(self.quality_scores)[-self.window_size:]
        recent_lengths = list(self.response_lengths)[-self.window_size:]
        recent_keywords = list(self.keyword_counts)[-self.window_size:]
        
        if len(recent_qualities) < self.window_size:
            return  # Not enough recent data
        
        # 1. Quality drift (using normalized difference)
        recent_quality_mean = np.mean(recent_qualities)
        quality_drift = abs(recent_quality_mean - self.baseline_quality_mean) / (self.baseline_quality_std + 1e-8)
        quality_drift_score.set(quality_drift)
        
        # 2. Length drift
        recent_length_mean = np.mean(recent_lengths)
        length_drift = abs(recent_length_mean - self.baseline_length_mean) / (self.baseline_length_std + 1e-8)
        length_drift_score.set(length_drift)
        
        # 3. Keyword distribution drift (using Chi-square-like metric)
        recent_kw_counts = Counter()
        for kw_count in recent_keywords:
            recent_kw_counts.update(kw_count)
        
        # Normalize by total counts
        baseline_total = sum(self.baseline_keywords.values())
        recent_total = sum(recent_kw_counts.values())
        
        kw_drift = 0.0
        if baseline_total > 0 and recent_total > 0:
            for keyword in self.tracked_keywords:
                baseline_freq = self.baseline_keywords[keyword] / baseline_total
                recent_freq = recent_kw_counts[keyword] / recent_total
                kw_drift += abs(baseline_freq - recent_freq)
            kw_drift /= len(self.tracked_keywords)
        
        keyword_drift_score.set(kw_drift)
        
        # Alert if any drift exceeds threshold
        drift_status = []
        if quality_drift > self.drift_threshold:
            drift_alerts.labels(metric_type='quality').inc()
            drift_status.append(f"Quality drift: {quality_drift:.3f}")
        
        if length_drift > self.drift_threshold:
            drift_alerts.labels(metric_type='length').inc()
            drift_status.append(f"Length drift: {length_drift:.3f}")
        
        if kw_drift > self.drift_threshold:
            drift_alerts.labels(metric_type='keywords').inc()
            drift_status.append(f"Keyword drift: {kw_drift:.3f}")
        
        if drift_status:
            if not self.drift_detected:
                print(f"⚠️ MODEL DRIFT DETECTED: {', '.join(drift_status)}")
                self.drift_detected = True
                
                # Log to MLflow
                try:
                    with mlflow.start_run(run_name=f"drift_alert_{datetime.now().strftime('%Y%m%d_%H%M')}"):
                        mlflow.log_metrics({
                            "quality_drift_score": quality_drift,
                            "length_drift_score": length_drift,
                            "keyword_drift_score": kw_drift,
                        })
                        mlflow.log_param("drift_detected", True)
                except Exception as e:
                    print(f"MLflow logging failed: {e}")
        else:
            if self.drift_detected:
                print("✅ Model drift resolved")
                self.drift_detected = False
    
    def get_drift_report(self) -> dict:
        """Get current drift status"""
        if not self.is_baseline_ready:
            return {"status": "baseline_not_ready", "samples_collected": len(self.quality_scores)}
        
        return {
            "status": "monitoring",
            "baseline_ready": True,
            "drift_detected": self.drift_detected,
            "metrics": {
                "quality_drift": quality_drift_score._value._value,
                "length_drift": length_drift_score._value._value,
                "keyword_drift": keyword_drift_score._value._value,
            },
            "threshold": self.drift_threshold,
            "samples_in_baseline": self.baseline_window,
            "samples_in_window": self.window_size
        }

# Global drift detector instance
drift_detector = DriftDetector(
    window_size=100,
    baseline_window=500,
    drift_threshold=0.15
)