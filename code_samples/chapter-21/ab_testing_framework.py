"""
A/B Testing Framework for LLM Model Comparison

This module provides a comprehensive A/B testing framework for comparing
different LLM models, providers, and configurations in production environments.
Enables data-driven decisions for model selection and optimization.

Key A/B testing concepts:
- Multi-armed bandit algorithms
- Statistical significance testing
- Performance metric tracking
- Automated traffic routing
- Real-time results monitoring

Author: Technical Interview Preparation Guide
"""

import asyncio
import json
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import numpy as np
from decimal import Decimal
import scipy.stats as stats

# =============================================================================
# DATA MODELS AND ENUMS
# =============================================================================

class TestStatus(Enum):
    """A/B test status"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class TrafficAllocation(Enum):
    """Traffic allocation strategies"""
    EQUAL_SPLIT = "equal_split"
    WEIGHTED = "weighted"
    EPSILON_GREEDY = "epsilon_greedy"
    THOMPSON_SAMPLING = "thompson_sampling"
    UCB = "upper_confidence_bound"

class MetricType(Enum):
    """Types of metrics to track"""
    LATENCY = "latency"
    COST = "cost"
    QUALITY_SCORE = "quality_score"
    USER_SATISFACTION = "user_satisfaction"
    SUCCESS_RATE = "success_rate"
    TOKEN_EFFICIENCY = "token_efficiency"
    ERROR_RATE = "error_rate"

@dataclass
class ModelVariant:
    """Configuration for a model variant in A/B test"""
    variant_id: str
    name: str
    provider: str
    model_name: str
    configuration: Dict[str, Any]
    expected_cost_per_request: Decimal
    description: str
    allocation_weight: float = 1.0

@dataclass
class TestMetrics:
    """Metrics collected for a variant"""
    variant_id: str
    sample_count: int = 0
    latency_sum: float = 0.0
    cost_sum: Decimal = Decimal('0')
    quality_scores: List[float] = field(default_factory=list)
    satisfaction_ratings: List[int] = field(default_factory=list)
    success_count: int = 0
    error_count: int = 0
    token_input_sum: int = 0
    token_output_sum: int = 0
    
    @property
    def average_latency(self) -> float:
        return self.latency_sum / self.sample_count if self.sample_count > 0 else 0.0
    
    @property
    def average_cost(self) -> Decimal:
        return self.cost_sum / self.sample_count if self.sample_count > 0 else Decimal('0')
    
    @property
    def average_quality_score(self) -> float:
        return statistics.mean(self.quality_scores) if self.quality_scores else 0.0
    
    @property
    def average_satisfaction(self) -> float:
        return statistics.mean(self.satisfaction_ratings) if self.satisfaction_ratings else 0.0
    
    @property
    def success_rate(self) -> float:
        total_requests = self.success_count + self.error_count
        return self.success_count / total_requests if total_requests > 0 else 0.0
    
    @property
    def token_efficiency(self) -> float:
        """Output tokens per input token - higher is better for generation tasks"""
        return self.token_output_sum / self.token_input_sum if self.token_input_sum > 0 else 0.0

@dataclass
class ExperimentRequest:
    """Request to be processed through A/B test"""
    request_id: str
    user_id: str
    session_id: str
    prompt: str
    task_type: str
    expected_response_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExperimentResult:
    """Result from processing a request through A/B test"""
    request_id: str
    variant_id: str
    response_content: str
    latency_ms: float
    cost: Decimal
    input_tokens: int
    output_tokens: int
    quality_score: Optional[float] = None
    user_satisfaction: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

# =============================================================================
# STATISTICAL ANALYSIS UTILITIES
# =============================================================================

class StatisticalAnalyzer:
    """Statistical analysis for A/B test results"""
    
    @staticmethod
    def calculate_confidence_interval(data: List[float], confidence_level: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for a dataset"""
        if len(data) < 2:
            return (0.0, 0.0)
        
        mean = statistics.mean(data)
        std_error = statistics.stdev(data) / (len(data) ** 0.5)
        
        # Use t-distribution for small samples
        if len(data) < 30:
            t_value = stats.t.ppf((1 + confidence_level) / 2, len(data) - 1)
            margin_of_error = t_value * std_error
        else:
            z_value = stats.norm.ppf((1 + confidence_level) / 2)
            margin_of_error = z_value * std_error
        
        return (mean - margin_of_error, mean + margin_of_error)
    
    @staticmethod
    def welch_t_test(data1: List[float], data2: List[float]) -> Tuple[float, float]:
        """Perform Welch's t-test for comparing two samples with potentially unequal variances"""
        if len(data1) < 2 or len(data2) < 2:
            return (0.0, 1.0)  # No statistical power
        
        statistic, p_value = stats.ttest_ind(data1, data2, equal_var=False)
        return (statistic, p_value)
    
    @staticmethod
    def calculate_effect_size(data1: List[float], data2: List[float]) -> float:
        """Calculate Cohen's d effect size"""
        if len(data1) < 2 or len(data2) < 2:
            return 0.0
        
        mean1, mean2 = statistics.mean(data1), statistics.mean(data2)
        
        # Pooled standard deviation
        n1, n2 = len(data1), len(data2)
        var1, var2 = statistics.variance(data1), statistics.variance(data2)
        pooled_std = ((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2)
        pooled_std = pooled_std ** 0.5
        
        if pooled_std == 0:
            return 0.0
        
        return (mean1 - mean2) / pooled_std
    
    @staticmethod
    def calculate_minimum_sample_size(
        effect_size: float, 
        alpha: float = 0.05, 
        power: float = 0.8
    ) -> int:
        """Calculate minimum sample size needed to detect an effect"""
        # Simplified calculation - in production would use more sophisticated methods
        z_alpha = abs(stats.norm.ppf(alpha / 2))
        z_beta = abs(stats.norm.ppf(1 - power))
        
        sample_size = 2 * ((z_alpha + z_beta) / effect_size) ** 2
        return max(int(sample_size), 10)  # Minimum of 10 samples

# =============================================================================
# MULTI-ARMED BANDIT ALGORITHMS
# =============================================================================

class MultiArmedBandit:
    """Multi-armed bandit algorithm for dynamic traffic allocation"""
    
    def __init__(self, variant_ids: List[str], algorithm: TrafficAllocation = TrafficAllocation.EPSILON_GREEDY):
        self.variant_ids = variant_ids
        self.algorithm = algorithm
        self.arm_counts = {vid: 0 for vid in variant_ids}
        self.arm_rewards = {vid: 0.0 for vid in variant_ids}
        self.epsilon = 0.1  # For epsilon-greedy
        self.alpha = 1.0  # For Thompson sampling
        self.beta = 1.0   # For Thompson sampling
        
    def select_variant(self, exclude_variants: Optional[Set[str]] = None) -> str:
        """Select variant based on chosen algorithm"""
        available_variants = [v for v in self.variant_ids if not exclude_variants or v not in exclude_variants]
        
        if not available_variants:
            return random.choice(self.variant_ids)
        
        if self.algorithm == TrafficAllocation.EQUAL_SPLIT:
            return random.choice(available_variants)
        
        elif self.algorithm == TrafficAllocation.EPSILON_GREEDY:
            return self._epsilon_greedy_selection(available_variants)
        
        elif self.algorithm == TrafficAllocation.THOMPSON_SAMPLING:
            return self._thompson_sampling_selection(available_variants)
        
        elif self.algorithm == TrafficAllocation.UCB:
            return self._ucb_selection(available_variants)
        
        else:
            return random.choice(available_variants)
    
    def _epsilon_greedy_selection(self, available_variants: List[str]) -> str:
        """Epsilon-greedy variant selection"""
        if random.random() < self.epsilon:
            # Explore: choose random variant
            return random.choice(available_variants)
        else:
            # Exploit: choose best performing variant
            best_variant = max(
                available_variants,
                key=lambda v: self.arm_rewards[v] / max(self.arm_counts[v], 1)
            )
            return best_variant
    
    def _thompson_sampling_selection(self, available_variants: List[str]) -> str:
        """Thompson sampling variant selection"""
        samples = {}
        
        for variant in available_variants:
            # Sample from Beta distribution
            successes = self.arm_rewards[variant] + self.alpha
            failures = (self.arm_counts[variant] - self.arm_rewards[variant]) + self.beta
            
            samples[variant] = np.random.beta(successes, failures)
        
        return max(samples, key=samples.get)
    
    def _ucb_selection(self, available_variants: List[str]) -> str:
        """Upper Confidence Bound variant selection"""
        total_counts = sum(self.arm_counts.values())
        
        if total_counts == 0:
            return random.choice(available_variants)
        
        ucb_values = {}
        
        for variant in available_variants:
            count = max(self.arm_counts[variant], 1)
            average_reward = self.arm_rewards[variant] / count
            
            # UCB1 formula
            confidence = (2 * np.log(total_counts) / count) ** 0.5
            ucb_values[variant] = average_reward + confidence
        
        return max(ucb_values, key=ucb_values.get)
    
    def update_reward(self, variant_id: str, reward: float):
        """Update reward for a variant"""
        self.arm_counts[variant_id] += 1
        self.arm_rewards[variant_id] += reward
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all arms"""
        summary = {}
        
        for variant in self.variant_ids:
            count = max(self.arm_counts[variant], 1)
            avg_reward = self.arm_rewards[variant] / count
            
            summary[variant] = {
                "pulls": self.arm_counts[variant],
                "total_reward": self.arm_rewards[variant],
                "average_reward": avg_reward,
                "selection_probability": count / sum(self.arm_counts.values()) if sum(self.arm_counts.values()) > 0 else 0
            }
        
        return summary

# =============================================================================
# A/B TEST FRAMEWORK
# =============================================================================

class ABTestFramework:
    """Comprehensive A/B testing framework for LLM models"""
    
    def __init__(self):
        self.active_experiments: Dict[str, 'ABExperiment'] = {}
        self.completed_experiments: Dict[str, 'ABExperiment'] = {}
        self.global_metrics: Dict[str, Any] = {}
        
    def create_experiment(
        self,
        experiment_name: str,
        description: str,
        variants: List[ModelVariant],
        primary_metric: MetricType,
        secondary_metrics: List[MetricType],
        traffic_allocation: TrafficAllocation = TrafficAllocation.EQUAL_SPLIT,
        minimum_sample_size: int = 100,
        minimum_runtime_hours: int = 24,
        significance_threshold: float = 0.05,
        target_user_segments: Optional[List[str]] = None
    ) -> str:
        """Create a new A/B experiment"""
        
        experiment_id = str(uuid.uuid4())
        
        experiment = ABExperiment(
            experiment_id=experiment_id,
            name=experiment_name,
            description=description,
            variants=variants,
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics,
            traffic_allocation=traffic_allocation,
            minimum_sample_size=minimum_sample_size,
            minimum_runtime_hours=minimum_runtime_hours,
            significance_threshold=significance_threshold,
            target_user_segments=target_user_segments or []
        )
        
        self.active_experiments[experiment_id] = experiment
        
        print(f"Created experiment '{experiment_name}' with ID: {experiment_id}")
        print(f"Variants: {[v.name for v in variants]}")
        print(f"Primary metric: {primary_metric.value}")
        
        return experiment_id
    
    def start_experiment(self, experiment_id: str) -> bool:
        """Start an A/B experiment"""
        if experiment_id not in self.active_experiments:
            return False
        
        experiment = self.active_experiments[experiment_id]
        return experiment.start()
    
    def pause_experiment(self, experiment_id: str) -> bool:
        """Pause an A/B experiment"""
        if experiment_id not in self.active_experiments:
            return False
        
        experiment = self.active_experiments[experiment_id]
        return experiment.pause()
    
    def process_request(self, experiment_id: str, request: ExperimentRequest) -> Optional[ExperimentResult]:
        """Process a request through an A/B experiment"""
        if experiment_id not in self.active_experiments:
            return None
        
        experiment = self.active_experiments[experiment_id]
        return asyncio.create_task(experiment.process_request(request))
    
    def get_experiment_results(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get current results for an experiment"""
        experiment = self.active_experiments.get(experiment_id) or self.completed_experiments.get(experiment_id)
        if not experiment:
            return None
        
        return experiment.get_results_summary()
    
    def check_experiment_completion(self, experiment_id: str) -> bool:
        """Check if experiment should be completed"""
        if experiment_id not in self.active_experiments:
            return False
        
        experiment = self.active_experiments[experiment_id]
        
        if experiment.should_complete():
            # Move to completed experiments
            experiment.complete()
            self.completed_experiments[experiment_id] = experiment
            del self.active_experiments[experiment_id]
            
            print(f"Experiment {experiment.name} completed with statistical significance")
            return True
        
        return False
    
    def get_framework_summary(self) -> Dict[str, Any]:
        """Get overall framework summary"""
        return {
            "active_experiments": len(self.active_experiments),
            "completed_experiments": len(self.completed_experiments),
            "total_requests_processed": sum(
                exp.total_requests for exp in list(self.active_experiments.values()) + list(self.completed_experiments.values())
            ),
            "experiments": {
                "active": [
                    {"id": eid, "name": exp.name, "status": exp.status.value, "runtime_hours": exp.runtime_hours}
                    for eid, exp in self.active_experiments.items()
                ],
                "completed": [
                    {"id": eid, "name": exp.name, "winner": exp.winner_variant_id}
                    for eid, exp in self.completed_experiments.items()
                ]
            }
        }

class ABExperiment:
    """Individual A/B experiment"""
    
    def __init__(
        self,
        experiment_id: str,
        name: str,
        description: str,
        variants: List[ModelVariant],
        primary_metric: MetricType,
        secondary_metrics: List[MetricType],
        traffic_allocation: TrafficAllocation,
        minimum_sample_size: int,
        minimum_runtime_hours: int,
        significance_threshold: float,
        target_user_segments: List[str]
    ):
        self.experiment_id = experiment_id
        self.name = name
        self.description = description
        self.variants = {v.variant_id: v for v in variants}
        self.primary_metric = primary_metric
        self.secondary_metrics = secondary_metrics
        self.traffic_allocation = traffic_allocation
        self.minimum_sample_size = minimum_sample_size
        self.minimum_runtime_hours = minimum_runtime_hours
        self.significance_threshold = significance_threshold
        self.target_user_segments = set(target_user_segments)
        
        # Runtime state
        self.status = TestStatus.DRAFT
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_requests = 0
        self.winner_variant_id: Optional[str] = None
        
        # Metrics tracking
        self.metrics: Dict[str, TestMetrics] = {
            vid: TestMetrics(variant_id=vid) for vid in self.variants.keys()
        }
        
        # Traffic allocation
        self.bandit = MultiArmedBandit(list(self.variants.keys()), traffic_allocation)
        
        # Statistical analyzer
        self.analyzer = StatisticalAnalyzer()
    
    def start(self) -> bool:
        """Start the experiment"""
        if self.status != TestStatus.DRAFT:
            return False
        
        self.status = TestStatus.RUNNING
        self.start_time = datetime.utcnow()
        
        print(f"Started experiment: {self.name}")
        return True
    
    def pause(self) -> bool:
        """Pause the experiment"""
        if self.status != TestStatus.RUNNING:
            return False
        
        self.status = TestStatus.PAUSED
        print(f"Paused experiment: {self.name}")
        return True
    
    def complete(self) -> bool:
        """Complete the experiment"""
        if self.status not in [TestStatus.RUNNING, TestStatus.PAUSED]:
            return False
        
        self.status = TestStatus.COMPLETED
        self.end_time = datetime.utcnow()
        
        # Determine winner based on primary metric
        self.winner_variant_id = self._determine_winner()
        
        print(f"Completed experiment: {self.name}")
        if self.winner_variant_id:
            winner_name = self.variants[self.winner_variant_id].name
            print(f"Winner: {winner_name}")
        
        return True
    
    async def process_request(self, request: ExperimentRequest) -> ExperimentResult:
        """Process a request through the experiment"""
        if self.status != TestStatus.RUNNING:
            raise ValueError("Experiment is not running")
        
        # Check if request is in target segment
        user_segment = request.metadata.get('user_segment', 'default')
        if self.target_user_segments and user_segment not in self.target_user_segments:
            # Route to control group or return None
            raise ValueError("User not in target segment")
        
        # Select variant using bandit algorithm
        selected_variant_id = self.bandit.select_variant()
        selected_variant = self.variants[selected_variant_id]
        
        # Simulate processing request with selected variant
        result = await self._simulate_request_processing(request, selected_variant)
        
        # Update metrics
        self._update_metrics(selected_variant_id, result)
        
        # Update bandit with reward
        reward = self._calculate_reward(result)
        self.bandit.update_reward(selected_variant_id, reward)
        
        self.total_requests += 1
        
        return result
    
    async def _simulate_request_processing(self, request: ExperimentRequest, variant: ModelVariant) -> ExperimentResult:
        """Simulate processing a request with a specific variant"""
        # In production, this would call the actual LLM API
        
        # Simulate different performance characteristics for different models
        base_latency = 1000  # 1 second base
        cost_multiplier = 1.0
        quality_base = 0.8
        
        if "gpt-4" in variant.model_name:
            base_latency *= 1.5
            cost_multiplier = 2.0
            quality_base = 0.9
        elif "gpt-3.5" in variant.model_name:
            base_latency *= 0.8
            cost_multiplier = 0.5
            quality_base = 0.8
        elif "claude" in variant.model_name:
            base_latency *= 1.2
            cost_multiplier = 1.5
            quality_base = 0.85
        
        # Add some randomness
        latency = base_latency * (0.8 + 0.4 * random.random())
        
        # Simulate processing
        await asyncio.sleep(latency / 1000)  # Convert to seconds
        
        input_tokens = len(request.prompt.split()) * 1.3  # Rough estimate
        output_tokens = input_tokens * 0.6  # Typical response length
        
        cost = variant.expected_cost_per_request * cost_multiplier
        
        # Simulate quality score (with some variance)
        quality_score = min(1.0, quality_base + random.gauss(0, 0.1))
        
        # Simulate user satisfaction (correlated with quality)
        satisfaction_base = min(5, max(1, int(quality_score * 5 + random.gauss(0, 0.5))))
        
        # Simulate occasional failures
        success = random.random() > 0.02  # 2% failure rate
        
        return ExperimentResult(
            request_id=request.request_id,
            variant_id=variant.variant_id,
            response_content=f"Generated response using {variant.model_name}",
            latency_ms=latency,
            cost=cost,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            quality_score=quality_score,
            user_satisfaction=satisfaction_base,
            success=success,
            error_message=None if success else "Simulated API error"
        )
    
    def _update_metrics(self, variant_id: str, result: ExperimentResult):
        """Update metrics for a variant"""
        metrics = self.metrics[variant_id]
        
        metrics.sample_count += 1
        metrics.latency_sum += result.latency_ms
        metrics.cost_sum += result.cost
        metrics.token_input_sum += result.input_tokens
        metrics.token_output_sum += result.output_tokens
        
        if result.quality_score is not None:
            metrics.quality_scores.append(result.quality_score)
        
        if result.user_satisfaction is not None:
            metrics.satisfaction_ratings.append(result.user_satisfaction)
        
        if result.success:
            metrics.success_count += 1
        else:
            metrics.error_count += 1
    
    def _calculate_reward(self, result: ExperimentResult) -> float:
        """Calculate reward for bandit algorithm based on primary metric"""
        if self.primary_metric == MetricType.LATENCY:
            # Lower latency is better
            return 1.0 / (result.latency_ms / 1000)  # Convert to seconds
        elif self.primary_metric == MetricType.COST:
            # Lower cost is better
            return 1.0 / max(float(result.cost), 0.001)
        elif self.primary_metric == MetricType.QUALITY_SCORE:
            return result.quality_score or 0.0
        elif self.primary_metric == MetricType.USER_SATISFACTION:
            return (result.user_satisfaction or 0) / 5.0  # Normalize to 0-1
        elif self.primary_metric == MetricType.SUCCESS_RATE:
            return 1.0 if result.success else 0.0
        else:
            return 1.0 if result.success else 0.0
    
    def should_complete(self) -> bool:
        """Check if experiment should be completed"""
        if self.status != TestStatus.RUNNING:
            return False
        
        # Check minimum runtime
        if self.start_time:
            runtime = datetime.utcnow() - self.start_time
            if runtime.total_seconds() < self.minimum_runtime_hours * 3600:
                return False
        
        # Check minimum sample size
        min_samples_per_variant = self.minimum_sample_size // len(self.variants)
        for metrics in self.metrics.values():
            if metrics.sample_count < min_samples_per_variant:
                return False
        
        # Check for statistical significance
        return self._has_statistical_significance()
    
    def _has_statistical_significance(self) -> bool:
        """Check if results show statistical significance"""
        variant_ids = list(self.variants.keys())
        
        if len(variant_ids) < 2:
            return False
        
        # Get primary metric data for each variant
        metric_data = {}
        
        for variant_id in variant_ids:
            metrics = self.metrics[variant_id]
            
            if self.primary_metric == MetricType.LATENCY:
                data = [metrics.average_latency] * metrics.sample_count if metrics.sample_count > 0 else []
            elif self.primary_metric == MetricType.COST:
                data = [float(metrics.average_cost)] * metrics.sample_count if metrics.sample_count > 0 else []
            elif self.primary_metric == MetricType.QUALITY_SCORE:
                data = metrics.quality_scores
            elif self.primary_metric == MetricType.USER_SATISFACTION:
                data = metrics.satisfaction_ratings
            elif self.primary_metric == MetricType.SUCCESS_RATE:
                data = [metrics.success_rate] * metrics.sample_count if metrics.sample_count > 0 else []
            else:
                data = []
            
            metric_data[variant_id] = data
        
        # Perform pairwise comparisons
        significant_pairs = 0
        total_pairs = 0
        
        for i, variant1 in enumerate(variant_ids):
            for variant2 in variant_ids[i+1:]:
                data1 = metric_data[variant1]
                data2 = metric_data[variant2]
                
                if len(data1) >= 10 and len(data2) >= 10:  # Minimum samples for meaningful test
                    _, p_value = self.analyzer.welch_t_test(data1, data2)
                    total_pairs += 1
                    
                    if p_value < self.significance_threshold:
                        significant_pairs += 1
        
        # Require at least one significant pair
        return significant_pairs > 0 and total_pairs > 0
    
    def _determine_winner(self) -> Optional[str]:
        """Determine winner based on primary metric"""
        if not self.metrics:
            return None
        
        best_variant_id = None
        best_score = None
        
        for variant_id, metrics in self.metrics.items():
            if metrics.sample_count == 0:
                continue
            
            if self.primary_metric == MetricType.LATENCY:
                score = -metrics.average_latency  # Negative because lower is better
            elif self.primary_metric == MetricType.COST:
                score = -float(metrics.average_cost)  # Negative because lower is better
            elif self.primary_metric == MetricType.QUALITY_SCORE:
                score = metrics.average_quality_score
            elif self.primary_metric == MetricType.USER_SATISFACTION:
                score = metrics.average_satisfaction
            elif self.primary_metric == MetricType.SUCCESS_RATE:
                score = metrics.success_rate
            else:
                score = metrics.success_rate
            
            if best_score is None or score > best_score:
                best_score = score
                best_variant_id = variant_id
        
        return best_variant_id
    
    @property
    def runtime_hours(self) -> float:
        """Get current runtime in hours"""
        if not self.start_time:
            return 0.0
        
        end_time = self.end_time or datetime.utcnow()
        return (end_time - self.start_time).total_seconds() / 3600
    
    def get_results_summary(self) -> Dict[str, Any]:
        """Get comprehensive results summary"""
        variant_results = {}
        
        for variant_id, metrics in self.metrics.items():
            variant = self.variants[variant_id]
            
            # Calculate confidence intervals
            latency_ci = self.analyzer.calculate_confidence_interval([metrics.average_latency] * metrics.sample_count) if metrics.sample_count > 1 else (0, 0)
            quality_ci = self.analyzer.calculate_confidence_interval(metrics.quality_scores) if len(metrics.quality_scores) > 1 else (0, 0)
            
            variant_results[variant_id] = {
                "name": variant.name,
                "model": variant.model_name,
                "provider": variant.provider,
                "sample_count": metrics.sample_count,
                "metrics": {
                    "average_latency_ms": round(metrics.average_latency, 1),
                    "latency_ci": [round(latency_ci[0], 1), round(latency_ci[1], 1)],
                    "average_cost": float(metrics.average_cost),
                    "average_quality_score": round(metrics.average_quality_score, 3),
                    "quality_ci": [round(quality_ci[0], 3), round(quality_ci[1], 3)],
                    "average_satisfaction": round(metrics.average_satisfaction, 1),
                    "success_rate": round(metrics.success_rate, 3),
                    "token_efficiency": round(metrics.token_efficiency, 2)
                },
                "is_winner": variant_id == self.winner_variant_id
            }
        
        # Statistical significance testing
        significance_results = {}
        variant_ids = list(self.variants.keys())
        
        for i, variant1 in enumerate(variant_ids):
            for variant2 in variant_ids[i+1:]:
                metrics1 = self.metrics[variant1]
                metrics2 = self.metrics[variant2]
                
                if self.primary_metric == MetricType.QUALITY_SCORE:
                    data1 = metrics1.quality_scores
                    data2 = metrics2.quality_scores
                elif self.primary_metric == MetricType.USER_SATISFACTION:
                    data1 = [float(x) for x in metrics1.satisfaction_ratings]
                    data2 = [float(x) for x in metrics2.satisfaction_ratings]
                else:
                    data1 = [metrics1.average_latency] * metrics1.sample_count
                    data2 = [metrics2.average_latency] * metrics2.sample_count
                
                if len(data1) > 1 and len(data2) > 1:
                    t_stat, p_value = self.analyzer.welch_t_test(data1, data2)
                    effect_size = self.analyzer.calculate_effect_size(data1, data2)
                    
                    significance_results[f"{variant1}_vs_{variant2}"] = {
                        "p_value": round(p_value, 6),
                        "statistically_significant": p_value < self.significance_threshold,
                        "effect_size": round(effect_size, 3),
                        "effect_interpretation": self._interpret_effect_size(effect_size)
                    }
        
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "status": self.status.value,
            "runtime_hours": round(self.runtime_hours, 1),
            "total_requests": self.total_requests,
            "primary_metric": self.primary_metric.value,
            "winner_variant": self.winner_variant_id,
            "variants": variant_results,
            "statistical_significance": significance_results,
            "bandit_performance": self.bandit.get_performance_summary(),
            "completion_criteria": {
                "minimum_sample_size_met": all(m.sample_count >= self.minimum_sample_size // len(self.variants) for m in self.metrics.values()),
                "minimum_runtime_met": self.runtime_hours >= self.minimum_runtime_hours,
                "statistical_significance_achieved": self._has_statistical_significance()
            }
        }
    
    def _interpret_effect_size(self, effect_size: float) -> str:
        """Interpret Cohen's d effect size"""
        abs_effect = abs(effect_size)
        
        if abs_effect < 0.2:
            return "negligible"
        elif abs_effect < 0.5:
            return "small"
        elif abs_effect < 0.8:
            return "medium"
        else:
            return "large"

# =============================================================================
# DEMONSTRATION
# =============================================================================

async def demonstrate_ab_testing():
    """Demonstrate the A/B testing framework"""
    
    print("=== LLM Model A/B Testing Framework Demo ===\n")
    
    # Initialize framework
    ab_framework = ABTestFramework()
    
    # Define model variants for comparison
    variants = [
        ModelVariant(
            variant_id="gpt4_optimized",
            name="GPT-4 Optimized",
            provider="openai",
            model_name="gpt-4o",
            configuration={"temperature": 0.1, "max_tokens": 1000},
            expected_cost_per_request=Decimal("0.03"),
            description="GPT-4 optimized for accuracy"
        ),
        ModelVariant(
            variant_id="gpt35_fast",
            name="GPT-3.5 Fast",
            provider="openai", 
            model_name="gpt-3.5-turbo",
            configuration={"temperature": 0.3, "max_tokens": 800},
            expected_cost_per_request=Decimal("0.002"),
            description="GPT-3.5 optimized for speed and cost"
        ),
        ModelVariant(
            variant_id="claude_balanced",
            name="Claude Balanced",
            provider="anthropic",
            model_name="claude-3-haiku-20240307",
            configuration={"temperature": 0.2, "max_tokens": 900},
            expected_cost_per_request=Decimal("0.015"),
            description="Claude optimized for balanced performance"
        )
    ]
    
    # Create experiment
    experiment_id = ab_framework.create_experiment(
        experiment_name="Legal Document Analysis Model Comparison",
        description="Compare different LLM models for legal document analysis tasks",
        variants=variants,
        primary_metric=MetricType.QUALITY_SCORE,
        secondary_metrics=[MetricType.LATENCY, MetricType.COST, MetricType.USER_SATISFACTION],
        traffic_allocation=TrafficAllocation.THOMPSON_SAMPLING,
        minimum_sample_size=150,
        minimum_runtime_hours=1,  # Short for demo
        significance_threshold=0.05
    )
    
    # Start experiment
    ab_framework.start_experiment(experiment_id)
    
    print(f"\nStarted experiment: {experiment_id}")
    print("Processing simulated requests...\n")
    
    # Simulate requests
    for i in range(200):
        request = ExperimentRequest(
            request_id=str(uuid.uuid4()),
            user_id=f"user_{i % 50}",  # 50 different users
            session_id=f"session_{i // 10}",  # Group sessions
            prompt=f"Analyze this legal clause for compliance risks: [Clause {i+1}]",
            task_type="legal_analysis",
            expected_response_type="risk_assessment",
            metadata={"user_segment": "legal_professionals"}
        )
        
        try:
            result = await ab_framework.process_request(experiment_id, request)
            
            if i % 50 == 0:  # Progress update
                print(f"Processed {i+1} requests...")
        
        except Exception as e:
            print(f"Error processing request {i}: {e}")
    
    # Check completion
    print("\nChecking experiment completion...")
    completed = ab_framework.check_experiment_completion(experiment_id)
    
    if not completed:
        # Force completion for demo
        experiment = ab_framework.active_experiments[experiment_id]
        experiment.complete()
        ab_framework.completed_experiments[experiment_id] = experiment
        del ab_framework.active_experiments[experiment_id]
    
    # Get results
    results = ab_framework.get_experiment_results(experiment_id)
    
    print("\n=== EXPERIMENT RESULTS ===")
    print(f"Experiment: {results['name']}")
    print(f"Status: {results['status']}")
    print(f"Runtime: {results['runtime_hours']} hours")
    print(f"Total Requests: {results['total_requests']}")
    print(f"Primary Metric: {results['primary_metric']}")
    
    if results['winner_variant']:
        winner_name = results['variants'][results['winner_variant']]['name']
        print(f"Winner: {winner_name}")
    
    print(f"\nVariant Performance:")
    print("-" * 80)
    
    for variant_id, variant_data in results['variants'].items():
        print(f"\n{variant_data['name']} ({variant_data['model']}):")
        print(f"  Sample Count: {variant_data['sample_count']}")
        print(f"  Avg Latency: {variant_data['metrics']['average_latency_ms']}ms")
        print(f"  Avg Cost: ${variant_data['metrics']['average_cost']:.4f}")
        print(f"  Quality Score: {variant_data['metrics']['average_quality_score']:.3f}")
        print(f"  User Satisfaction: {variant_data['metrics']['average_satisfaction']:.1f}/5")
        print(f"  Success Rate: {variant_data['metrics']['success_rate']:.1%}")
        print(f"  Token Efficiency: {variant_data['metrics']['token_efficiency']:.2f}")
        
        if variant_data['is_winner']:
            print("  🏆 WINNER")
    
    print(f"\nStatistical Significance:")
    print("-" * 50)
    
    for comparison, stats in results['statistical_significance'].items():
        variants = comparison.replace('_vs_', ' vs ')
        significance = "✓ Significant" if stats['statistically_significant'] else "✗ Not Significant"
        print(f"{variants}: p={stats['p_value']:.4f} ({significance})")
        print(f"  Effect Size: {stats['effect_size']:.3f} ({stats['effect_interpretation']})")
    
    print(f"\nCompletion Criteria:")
    criteria = results['completion_criteria']
    print(f"  Minimum Sample Size: {'✓' if criteria['minimum_sample_size_met'] else '✗'}")
    print(f"  Minimum Runtime: {'✓' if criteria['minimum_runtime_met'] else '✗'}")
    print(f"  Statistical Significance: {'✓' if criteria['statistical_significance_achieved'] else '✗'}")
    
    print(f"\nBandit Algorithm Performance:")
    for variant_id, perf in results['bandit_performance'].items():
        variant_name = results['variants'][variant_id]['name']
        print(f"  {variant_name}: {perf['pulls']} pulls, {perf['selection_probability']:.1%} selection rate")
    
    # Framework summary
    print(f"\n=== FRAMEWORK SUMMARY ===")
    framework_summary = ab_framework.get_framework_summary()
    print(f"Active Experiments: {framework_summary['active_experiments']}")
    print(f"Completed Experiments: {framework_summary['completed_experiments']}")
    print(f"Total Requests Processed: {framework_summary['total_requests_processed']}")

if __name__ == "__main__":
    # Run the A/B testing demonstration
    asyncio.run(demonstrate_ab_testing())