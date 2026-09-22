"""
Cost Optimization System for Enterprise LLM Applications

This module demonstrates comprehensive cost optimization strategies for large-scale
LLM deployments like those used at Lawstronaut (processing millions of legal documents)
and Optimizely (handling thousands of concurrent AI interactions).

Key concepts covered:
- Real-time cost tracking and analysis
- Intelligent model selection based on cost/quality trade-offs
- Token optimization and prompt engineering
- Caching strategies for cost reduction
- Predictive cost modeling and budgeting

Real-world applications:
- Legal document processing with cost constraints
- Customer service chatbots with budget optimization
- Content generation with ROI tracking

Author: Technical Interview Preparation Guide
"""

import asyncio
import json
import time
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
from decimal import Decimal, ROUND_HALF_UP
import statistics
import numpy as np
from abc import ABC, abstractmethod

# =============================================================================
# COST TRACKING DATA MODELS
# =============================================================================

class CostCategory(Enum):
    """Categories for cost attribution"""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    API_CALLS = "api_calls"
    PROCESSING = "processing"

class ModelTier(Enum):
    """Model tiers for cost optimization"""
    BASIC = "basic"
    STANDARD = "standard" 
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

@dataclass
class CostMetric:
    """Individual cost measurement"""
    timestamp: datetime
    provider: str
    model: str
    operation_type: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    latency_ms: float
    user_id: Optional[str] = None
    application: str = "default"
    request_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.request_id:
            self.request_id = hashlib.md5(
                f"{self.timestamp}{self.provider}{self.model}{time.time()}".encode()
            ).hexdigest()[:12]

@dataclass
class CostBudget:
    """Budget configuration for cost control"""
    name: str
    total_budget: Decimal
    period_days: int
    categories: Dict[CostCategory, Decimal]
    alert_thresholds: Dict[str, float]  # percentage -> action
    auto_actions: Dict[str, str]  # threshold -> action
    start_date: datetime
    
    @property
    def daily_budget(self) -> Decimal:
        return self.total_budget / self.period_days
    
    @property
    def end_date(self) -> datetime:
        return self.start_date + timedelta(days=self.period_days)

@dataclass
class OptimizationRecommendation:
    """Cost optimization recommendation"""
    recommendation_id: str
    title: str
    description: str
    potential_savings_usd: Decimal
    potential_savings_percentage: float
    implementation_effort: str  # "low", "medium", "high"
    risk_level: str  # "low", "medium", "high"
    estimated_impact_days: int
    implementation_steps: List[str]
    affected_applications: List[str]
    confidence_score: float  # 0.0 to 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)

# =============================================================================
# TOKEN OPTIMIZATION ENGINE
# =============================================================================

class TokenOptimizer:
    """Advanced token optimization for cost reduction"""
    
    def __init__(self):
        # Common token patterns and their optimizations
        self.optimization_patterns = {
            "repetitive_phrases": {
                "pattern": r'\b(\w+(?:\s+\w+)*)\s+\1\b',
                "replacement": r'\1',
                "description": "Remove repetitive phrases"
            },
            "excessive_whitespace": {
                "pattern": r'\s+',
                "replacement": ' ',
                "description": "Normalize whitespace"
            },
            "redundant_punctuation": {
                "pattern": r'[.!?]{2,}',
                "replacement": '.',
                "description": "Reduce redundant punctuation"
            }
        }
        
        # Token estimation models
        self.token_estimators = {
            "gpt": lambda text: len(text.split()) * 1.3,
            "claude": lambda text: len(text.split()) * 1.25,
            "accurate": self._accurate_token_count
        }
    
    def optimize_prompt(self, prompt: str, target_reduction: float = 0.2) -> Dict[str, Any]:
        """
        Optimize prompt to reduce token count while preserving meaning
        
        Args:
            prompt: Input prompt text
            target_reduction: Target reduction percentage (0.0 to 1.0)
            
        Returns:
            Dictionary with optimized prompt and metrics
        """
        original_tokens = self.estimate_tokens(prompt)
        target_tokens = int(original_tokens * (1 - target_reduction))
        
        optimizations_applied = []
        current_prompt = prompt
        
        # Apply optimization patterns
        for pattern_name, pattern_config in self.optimization_patterns.items():
            import re
            old_prompt = current_prompt
            current_prompt = re.sub(
                pattern_config["pattern"],
                pattern_config["replacement"],
                current_prompt
            )
            
            if old_prompt != current_prompt:
                optimizations_applied.append(pattern_name)
        
        # Advanced optimizations if still above target
        current_tokens = self.estimate_tokens(current_prompt)
        if current_tokens > target_tokens:
            current_prompt = self._advanced_optimization(current_prompt, target_tokens)
            current_tokens = self.estimate_tokens(current_prompt)
        
        reduction_achieved = 1 - (current_tokens / original_tokens)
        
        return {
            "original_prompt": prompt,
            "optimized_prompt": current_prompt,
            "original_tokens": original_tokens,
            "optimized_tokens": current_tokens,
            "reduction_percentage": reduction_achieved,
            "target_achieved": reduction_achieved >= target_reduction * 0.9,
            "optimizations_applied": optimizations_applied,
            "estimated_cost_savings": self._calculate_cost_savings(
                original_tokens, current_tokens
            )
        }
    
    def _advanced_optimization(self, prompt: str, target_tokens: int) -> str:
        """Apply advanced optimization techniques"""
        sentences = prompt.split('. ')
        
        # Prioritize sentences by information density
        sentence_scores = []
        for sentence in sentences:
            # Simple scoring based on unique words and length
            words = set(sentence.lower().split())
            score = len(words) / max(len(sentence.split()), 1)
            sentence_scores.append((sentence, score))
        
        # Sort by score (descending) and keep highest value sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Reconstruct prompt with top sentences until target is met
        optimized_sentences = []
        current_tokens = 0
        
        for sentence, score in sentence_scores:
            sentence_tokens = self.estimate_tokens(sentence)
            if current_tokens + sentence_tokens <= target_tokens:
                optimized_sentences.append(sentence)
                current_tokens += sentence_tokens
            else:
                break
        
        # Maintain original order of selected sentences
        original_order_sentences = []
        for sentence in sentences:
            if sentence in [s for s, _ in sentence_scores[:len(optimized_sentences)]]:
                original_order_sentences.append(sentence)
        
        return '. '.join(original_order_sentences)
    
    def estimate_tokens(self, text: str, model_type: str = "gpt") -> int:
        """Estimate token count for given text"""
        estimator = self.token_estimators.get(model_type, self.token_estimators["gpt"])
        return int(estimator(text))
    
    def _accurate_token_count(self, text: str) -> int:
        """More accurate token counting (simplified implementation)"""
        # In production, use actual tokenizer like tiktoken
        # This is a simplified approximation
        words = text.split()
        # Account for subword tokenization
        token_count = 0
        for word in words:
            if len(word) <= 4:
                token_count += 1
            elif len(word) <= 8:
                token_count += 2
            else:
                token_count += max(2, len(word) // 4)
        
        return token_count
    
    def _calculate_cost_savings(self, original_tokens: int, optimized_tokens: int) -> Dict[str, Decimal]:
        """Calculate potential cost savings"""
        # Typical pricing per 1k tokens
        pricing = {
            "gpt-4": {"input": Decimal("0.03"), "output": Decimal("0.06")},
            "gpt-3.5": {"input": Decimal("0.0015"), "output": Decimal("0.002")},
            "claude": {"input": Decimal("0.015"), "output": Decimal("0.075")}
        }
        
        savings = {}
        token_reduction = original_tokens - optimized_tokens
        
        for model, prices in pricing.items():
            input_savings = (token_reduction / 1000) * prices["input"]
            output_savings = (token_reduction / 1000) * prices["output"]
            savings[model] = {
                "input_savings": input_savings,
                "output_savings": output_savings,
                "total_savings": input_savings + output_savings
            }
        
        return savings

# =============================================================================
# INTELLIGENT MODEL SELECTOR
# =============================================================================

class ModelSelector:
    """Intelligent model selection based on cost/quality trade-offs"""
    
    def __init__(self):
        # Model capability matrix
        self.model_capabilities = {
            "gpt-4o": {
                "reasoning": 0.95,
                "creativity": 0.90,
                "code": 0.92,
                "analysis": 0.94,
                "cost_per_1k_tokens": Decimal("0.005"),
                "tier": ModelTier.PREMIUM
            },
            "gpt-4-turbo": {
                "reasoning": 0.93,
                "creativity": 0.88,
                "code": 0.90,
                "analysis": 0.92,
                "cost_per_1k_tokens": Decimal("0.01"),
                "tier": ModelTier.PREMIUM
            },
            "gpt-3.5-turbo": {
                "reasoning": 0.75,
                "creativity": 0.70,
                "code": 0.78,
                "analysis": 0.72,
                "cost_per_1k_tokens": Decimal("0.0015"),
                "tier": ModelTier.STANDARD
            },
            "claude-3-5-sonnet-20241022": {
                "reasoning": 0.92,
                "creativity": 0.85,
                "code": 0.88,
                "analysis": 0.95,
                "cost_per_1k_tokens": Decimal("0.003"),
                "tier": ModelTier.PREMIUM
            },
            "claude-3-haiku-20240307": {
                "reasoning": 0.78,
                "creativity": 0.72,
                "code": 0.75,
                "analysis": 0.80,
                "cost_per_1k_tokens": Decimal("0.00025"),
                "tier": ModelTier.BASIC
            }
        }
        
        # Task type requirements
        self.task_requirements = {
            "legal_analysis": {
                "reasoning": 0.90,
                "analysis": 0.95,
                "creativity": 0.60,
                "code": 0.30
            },
            "customer_service": {
                "reasoning": 0.70,
                "analysis": 0.65,
                "creativity": 0.75,
                "code": 0.20
            },
            "code_generation": {
                "reasoning": 0.85,
                "analysis": 0.80,
                "creativity": 0.70,
                "code": 0.95
            },
            "content_writing": {
                "reasoning": 0.75,
                "analysis": 0.70,
                "creativity": 0.90,
                "code": 0.20
            },
            "data_analysis": {
                "reasoning": 0.88,
                "analysis": 0.95,
                "creativity": 0.60,
                "code": 0.85
            }
        }
    
    def recommend_model(self, task_type: str, quality_threshold: float = 0.8,
                       budget_constraint: Optional[Decimal] = None,
                       estimated_tokens: int = 1000) -> Dict[str, Any]:
        """
        Recommend optimal model based on task requirements and constraints
        
        Args:
            task_type: Type of task (must be in task_requirements)
            quality_threshold: Minimum quality score required (0.0 to 1.0)
            budget_constraint: Maximum cost per request
            estimated_tokens: Estimated token count for cost calculation
            
        Returns:
            Model recommendation with rationale
        """
        if task_type not in self.task_requirements:
            raise ValueError(f"Unknown task type: {task_type}")
        
        requirements = self.task_requirements[task_type]
        candidates = []
        
        # Evaluate each model
        for model_name, capabilities in self.model_capabilities.items():
            # Calculate quality score
            quality_score = sum(
                requirements[capability] * capabilities[capability]
                for capability in requirements
            ) / sum(requirements.values())
            
            # Calculate estimated cost
            estimated_cost = (estimated_tokens / 1000) * capabilities["cost_per_1k_tokens"]
            
            # Check constraints
            meets_quality = quality_score >= quality_threshold
            meets_budget = budget_constraint is None or estimated_cost <= budget_constraint
            
            if meets_quality and meets_budget:
                candidates.append({
                    "model": model_name,
                    "quality_score": quality_score,
                    "estimated_cost": estimated_cost,
                    "cost_per_quality": float(estimated_cost / quality_score),
                    "tier": capabilities["tier"],
                    "capabilities": capabilities
                })
        
        if not candidates:
            return {
                "recommended_model": None,
                "reason": "No models meet the specified constraints",
                "alternatives": self._get_alternative_recommendations(
                    task_type, quality_threshold, budget_constraint, estimated_tokens
                )
            }
        
        # Sort by cost-effectiveness (cost per quality point)
        candidates.sort(key=lambda x: x["cost_per_quality"])
        best_candidate = candidates[0]
        
        return {
            "recommended_model": best_candidate["model"],
            "quality_score": best_candidate["quality_score"],
            "estimated_cost": float(best_candidate["estimated_cost"]),
            "cost_effectiveness": best_candidate["cost_per_quality"],
            "tier": best_candidate["tier"].value,
            "reason": f"Best cost-effectiveness for {task_type}",
            "alternatives": [
                {
                    "model": c["model"],
                    "quality_score": c["quality_score"],
                    "estimated_cost": float(c["estimated_cost"]),
                    "reason": "Alternative option"
                }
                for c in candidates[1:3]  # Top 3 alternatives
            ]
        }
    
    def _get_alternative_recommendations(self, task_type: str, quality_threshold: float,
                                       budget_constraint: Optional[Decimal],
                                       estimated_tokens: int) -> List[Dict[str, Any]]:
        """Get alternative recommendations when constraints can't be met"""
        alternatives = []
        
        # Suggest lower quality threshold
        if quality_threshold > 0.6:
            alt_recommendation = self.recommend_model(
                task_type, quality_threshold * 0.9, budget_constraint, estimated_tokens
            )
            if alt_recommendation["recommended_model"]:
                alternatives.append({
                    "type": "lower_quality",
                    "description": f"Lower quality threshold to {quality_threshold * 0.9:.1f}",
                    "recommendation": alt_recommendation
                })
        
        # Suggest higher budget
        if budget_constraint:
            alt_recommendation = self.recommend_model(
                task_type, quality_threshold, budget_constraint * Decimal("1.5"), estimated_tokens
            )
            if alt_recommendation["recommended_model"]:
                alternatives.append({
                    "type": "higher_budget",
                    "description": f"Increase budget to ${budget_constraint * Decimal('1.5'):.4f}",
                    "recommendation": alt_recommendation
                })
        
        return alternatives

# =============================================================================
# COMPREHENSIVE COST TRACKER
# =============================================================================

class CostTracker:
    """Advanced cost tracking and analysis system"""
    
    def __init__(self):
        self.cost_metrics: List[CostMetric] = []
        self.budgets: Dict[str, CostBudget] = {}
        self.alerts_sent: Dict[str, datetime] = {}
        self.cost_cache = {}
        
        # Initialize token optimizer and model selector
        self.token_optimizer = TokenOptimizer()
        self.model_selector = ModelSelector()
    
    def record_cost(self, metric: CostMetric):
        """Record a new cost metric"""
        self.cost_metrics.append(metric)
        
        # Update cache
        self._update_cost_cache(metric)
        
        # Check budget alerts
        self._check_budget_alerts(metric)
    
    def get_cost_summary(self, start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get comprehensive cost summary for specified period"""
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.utcnow()
        
        # Filter metrics by date range
        relevant_metrics = [
            m for m in self.cost_metrics
            if start_date <= m.timestamp <= end_date
        ]
        
        if not relevant_metrics:
            return {"error": "No metrics found for specified period"}
        
        # Calculate summary statistics
        total_cost = sum(m.cost_usd for m in relevant_metrics)
        total_tokens = sum(m.input_tokens + m.output_tokens for m in relevant_metrics)
        average_cost_per_request = total_cost / len(relevant_metrics)
        
        # Group by different dimensions
        by_provider = defaultdict(Decimal)
        by_model = defaultdict(Decimal)
        by_application = defaultdict(Decimal)
        by_day = defaultdict(Decimal)
        
        for metric in relevant_metrics:
            by_provider[metric.provider] += metric.cost_usd
            by_model[metric.model] += metric.cost_usd
            by_application[metric.application] += metric.cost_usd
            by_day[metric.timestamp.date()] += metric.cost_usd
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": (end_date - start_date).days
            },
            "summary": {
                "total_cost": float(total_cost),
                "total_requests": len(relevant_metrics),
                "total_tokens": total_tokens,
                "average_cost_per_request": float(average_cost_per_request),
                "average_cost_per_token": float(total_cost / total_tokens) if total_tokens > 0 else 0
            },
            "breakdown": {
                "by_provider": {k: float(v) for k, v in by_provider.items()},
                "by_model": {k: float(v) for k, v in by_model.items()},
                "by_application": {k: float(v) for k, v in by_application.items()},
                "by_day": {k.isoformat(): float(v) for k, v in by_day.items()}
            },
            "trends": self._calculate_trends(relevant_metrics),
            "optimization_opportunities": self._identify_optimization_opportunities(relevant_metrics)
        }
    
    def _calculate_trends(self, metrics: List[CostMetric]) -> Dict[str, Any]:
        """Calculate cost trends and patterns"""
        if len(metrics) < 2:
            return {"insufficient_data": True}
        
        # Sort by timestamp
        sorted_metrics = sorted(metrics, key=lambda x: x.timestamp)
        
        # Calculate daily costs
        daily_costs = defaultdict(Decimal)
        for metric in sorted_metrics:
            day = metric.timestamp.date()
            daily_costs[day] += metric.cost_usd
        
        daily_values = list(daily_costs.values())
        
        if len(daily_values) >= 7:
            # Calculate weekly trend
            recent_week = daily_values[-7:]
            previous_week = daily_values[-14:-7] if len(daily_values) >= 14 else daily_values[:-7]
            
            recent_avg = statistics.mean(recent_week)
            previous_avg = statistics.mean(previous_week) if previous_week else recent_avg
            
            trend_percentage = ((recent_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0
        else:
            trend_percentage = 0
        
        return {
            "daily_average": float(statistics.mean(daily_values)),
            "daily_std_dev": float(statistics.stdev(daily_values)) if len(daily_values) > 1 else 0,
            "trend_percentage": float(trend_percentage),
            "trend_direction": "increasing" if trend_percentage > 5 else "decreasing" if trend_percentage < -5 else "stable"
        }
    
    def _identify_optimization_opportunities(self, metrics: List[CostMetric]) -> List[OptimizationRecommendation]:
        """Identify specific cost optimization opportunities"""
        recommendations = []
        
        # Analyze expensive models usage
        model_costs = defaultdict(list)
        for metric in metrics:
            model_costs[metric.model].append(metric.cost_usd)
        
        for model, costs in model_costs.items():
            if len(costs) > 10:  # Sufficient data
                avg_cost = statistics.mean(costs)
                total_cost = sum(costs)
                
                # Check if expensive model is being overused
                if avg_cost > Decimal("0.01") and len(costs) > 100:  # High cost, high usage
                    # Estimate savings with cheaper model
                    potential_savings = total_cost * Decimal("0.3")  # Conservative estimate
                    
                    rec = OptimizationRecommendation(
                        recommendation_id=f"model_downgrade_{model}_{int(time.time())}",
                        title=f"Consider cheaper alternatives to {model}",
                        description=f"Model {model} is used frequently with high per-request costs. "
                                  f"Consider using cheaper alternatives for suitable tasks.",
                        potential_savings_usd=potential_savings,
                        potential_savings_percentage=30.0,
                        implementation_effort="medium",
                        risk_level="low",
                        estimated_impact_days=7,
                        implementation_steps=[
                            f"Analyze {model} usage patterns",
                            "Identify tasks suitable for cheaper models",
                            "A/B test cheaper alternatives",
                            "Gradually migrate suitable workloads"
                        ],
                        affected_applications=[m.application for m in metrics if m.model == model],
                        confidence_score=0.8
                    )
                    recommendations.append(rec)
        
        # Analyze token optimization opportunities
        high_token_requests = [m for m in metrics if (m.input_tokens + m.output_tokens) > 2000]
        
        if len(high_token_requests) > 20:
            total_tokens = sum(m.input_tokens + m.output_tokens for m in high_token_requests)
            potential_token_savings = total_tokens * 0.25  # 25% reduction estimate
            cost_per_token = sum(m.cost_usd for m in high_token_requests) / total_tokens
            potential_cost_savings = Decimal(str(potential_token_savings)) * Decimal(str(cost_per_token))
            
            rec = OptimizationRecommendation(
                recommendation_id=f"token_optimization_{int(time.time())}",
                title="Optimize prompts to reduce token usage",
                description=f"Detected {len(high_token_requests)} requests with high token counts. "
                          f"Prompt optimization could reduce costs significantly.",
                potential_savings_usd=potential_cost_savings,
                potential_savings_percentage=25.0,
                implementation_effort="low",
                risk_level="low",
                estimated_impact_days=3,
                implementation_steps=[
                    "Analyze high-token prompts",
                    "Apply automated prompt optimization",
                    "Test optimized prompts for quality",
                    "Deploy optimizations gradually"
                ],
                affected_applications=list(set(m.application for m in high_token_requests)),
                confidence_score=0.9
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _update_cost_cache(self, metric: CostMetric):
        """Update internal cost cache for faster queries"""
        cache_key = f"{metric.timestamp.date()}_{metric.provider}_{metric.model}"
        if cache_key not in self.cost_cache:
            self.cost_cache[cache_key] = {
                "total_cost": Decimal("0"),
                "request_count": 0,
                "total_tokens": 0
            }
        
        self.cost_cache[cache_key]["total_cost"] += metric.cost_usd
        self.cost_cache[cache_key]["request_count"] += 1
        self.cost_cache[cache_key]["total_tokens"] += metric.input_tokens + metric.output_tokens
    
    def _check_budget_alerts(self, metric: CostMetric):
        """Check and send budget alerts if necessary"""
        for budget_name, budget in self.budgets.items():
            if budget.start_date <= metric.timestamp <= budget.end_date:
                current_spend = self._calculate_current_spend(budget)
                
                for threshold_str, action in budget.alert_thresholds.items():
                    threshold = float(threshold_str) / 100
                    budget_used = float(current_spend / budget.total_budget)
                    
                    if budget_used >= threshold:
                        alert_key = f"{budget_name}_{threshold_str}"
                        
                        # Check if alert already sent recently
                        if alert_key not in self.alerts_sent or \
                           (datetime.utcnow() - self.alerts_sent[alert_key]) > timedelta(hours=1):
                            
                            self._send_budget_alert(budget, threshold, current_spend, action)
                            self.alerts_sent[alert_key] = datetime.utcnow()
    
    def _calculate_current_spend(self, budget: CostBudget) -> Decimal:
        """Calculate current spend for budget period"""
        relevant_metrics = [
            m for m in self.cost_metrics
            if budget.start_date <= m.timestamp <= budget.end_date
        ]
        return sum(m.cost_usd for m in relevant_metrics)
    
    def _send_budget_alert(self, budget: CostBudget, threshold: float, 
                          current_spend: Decimal, action: str):
        """Send budget alert (in production, integrate with alerting system)"""
        logging.warning(
            f"Budget Alert: {budget.name} has used {threshold*100:.1f}% "
            f"(${current_spend:.2f} of ${budget.total_budget:.2f}). "
            f"Action: {action}"
        )
    
    def create_budget(self, budget: CostBudget):
        """Create a new cost budget"""
        self.budgets[budget.name] = budget
    
    def predict_monthly_cost(self, days_of_data: int = 7) -> Dict[str, Any]:
        """Predict monthly costs based on recent usage patterns"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_of_data)
        recent_metrics = [m for m in self.cost_metrics if m.timestamp >= cutoff_date]
        
        if len(recent_metrics) < 10:
            return {"error": "Insufficient data for prediction"}
        
        # Calculate daily average
        daily_costs = defaultdict(Decimal)
        for metric in recent_metrics:
            day = metric.timestamp.date()
            daily_costs[day] += metric.cost_usd
        
        if not daily_costs:
            return {"error": "No cost data available"}
        
        daily_average = sum(daily_costs.values()) / len(daily_costs)
        monthly_prediction = daily_average * 30
        
        # Calculate confidence interval
        daily_values = list(daily_costs.values())
        std_dev = statistics.stdev(daily_values) if len(daily_values) > 1 else Decimal("0")
        confidence_range = std_dev * Decimal("1.96") * Decimal("30")  # 95% confidence interval
        
        return {
            "predicted_monthly_cost": float(monthly_prediction),
            "confidence_interval": {
                "lower": float(monthly_prediction - confidence_range),
                "upper": float(monthly_prediction + confidence_range)
            },
            "daily_average": float(daily_average),
            "data_period_days": days_of_data,
            "prediction_confidence": "high" if std_dev < daily_average * Decimal("0.3") else "medium"
        }

# =============================================================================
# INTELLIGENT CACHING FOR COST REDUCTION
# =============================================================================

class CostOptimizedCache:
    """Advanced caching system optimized for LLM cost reduction"""
    
    def __init__(self, max_cache_size: int = 10000):
        self.cache = {}
        self.access_counts = defaultdict(int)
        self.cost_savings = defaultdict(Decimal)
        self.max_size = max_cache_size
        
        # Cache policies
        self.ttl_by_cost = {
            # Higher cost requests get longer TTL
            Decimal("0.001"): 3600,    # 1 hour for low cost
            Decimal("0.01"): 7200,     # 2 hours for medium cost
            Decimal("0.1"): 86400,     # 1 day for high cost
            Decimal("1.0"): 604800     # 1 week for very high cost
        }
    
    def generate_cache_key(self, prompt: str, model: str, temperature: float) -> str:
        """Generate consistent cache key"""
        key_data = f"{prompt}|{model}|{temperature:.2f}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached response if valid"""
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            
            # Check TTL
            if time.time() < cached_item["expires_at"]:
                self.access_counts[cache_key] += 1
                return cached_item["data"]
            else:
                # Expired, remove from cache
                del self.cache[cache_key]
        
        return None
    
    def put(self, cache_key: str, data: Dict[str, Any], cost: Decimal):
        """Store response in cache with cost-based TTL"""
        # Determine TTL based on cost
        ttl = self._get_ttl_for_cost(cost)
        
        # Evict if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_least_valuable()
        
        self.cache[cache_key] = {
            "data": data,
            "stored_at": time.time(),
            "expires_at": time.time() + ttl,
            "cost": cost,
            "access_count": 0
        }
    
    def _get_ttl_for_cost(self, cost: Decimal) -> int:
        """Get TTL based on request cost"""
        for threshold, ttl in sorted(self.ttl_by_cost.items()):
            if cost <= threshold:
                return ttl
        
        # For very expensive requests, use longest TTL
        return max(self.ttl_by_cost.values())
    
    def _evict_least_valuable(self):
        """Evict least valuable cache entries"""
        if not self.cache:
            return
        
        # Calculate value score for each cached item
        item_values = []
        current_time = time.time()
        
        for cache_key, cached_item in self.cache.items():
            age = current_time - cached_item["stored_at"]
            access_frequency = self.access_counts.get(cache_key, 0) / max(age / 3600, 0.1)  # per hour
            cost_value = float(cached_item["cost"])
            
            # Value score combines cost savings and access frequency
            value_score = cost_value * access_frequency
            item_values.append((cache_key, value_score))
        
        # Sort by value (ascending) and remove lowest value items
        item_values.sort(key=lambda x: x[1])
        
        # Remove bottom 10% of cache
        items_to_remove = max(1, len(item_values) // 10)
        for cache_key, _ in item_values[:items_to_remove]:
            if cache_key in self.cache:
                del self.cache[cache_key]
            if cache_key in self.access_counts:
                del self.access_counts[cache_key]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        if not self.cache:
            return {"cache_size": 0, "total_cost_savings": 0}
        
        current_time = time.time()
        valid_entries = 0
        total_cost_savings = Decimal("0")
        
        for cache_key, cached_item in self.cache.items():
            if current_time < cached_item["expires_at"]:
                valid_entries += 1
                access_count = self.access_counts.get(cache_key, 0)
                cost_per_request = cached_item["cost"]
                total_cost_savings += cost_per_request * access_count
        
        hit_rate = len([k for k in self.access_counts if self.access_counts[k] > 0]) / max(len(self.cache), 1)
        
        return {
            "cache_size": len(self.cache),
            "valid_entries": valid_entries,
            "hit_rate": hit_rate,
            "total_accesses": sum(self.access_counts.values()),
            "total_cost_savings": float(total_cost_savings),
            "average_savings_per_hit": float(total_cost_savings / max(sum(self.access_counts.values()), 1))
        }

# =============================================================================
# COMPREHENSIVE COST OPTIMIZATION SYSTEM
# =============================================================================

class CostOptimizationSystem:
    """Comprehensive cost optimization system integrating all components"""
    
    def __init__(self):
        self.cost_tracker = CostTracker()
        self.cache = CostOptimizedCache()
        self.active_optimizations = {}
        self.optimization_results = []
    
    async def optimize_request(self, prompt: str, model: str, 
                             task_type: str = "general",
                             budget_constraint: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Comprehensively optimize a request for cost while maintaining quality
        
        Returns optimized request parameters and expected savings
        """
        optimization_result = {
            "original_request": {
                "prompt": prompt,
                "model": model,
                "task_type": task_type
            },
            "optimizations_applied": [],
            "cost_analysis": {},
            "recommendations": {}
        }
        
        # 1. Check cache first
        cache_key = self.cache.generate_cache_key(prompt, model, 0.7)
        cached_response = self.cache.get(cache_key)
        
        if cached_response:
            optimization_result["optimizations_applied"].append("cache_hit")
            optimization_result["cost_analysis"]["cache_savings"] = True
            return optimization_result
        
        # 2. Optimize prompt tokens
        token_optimization = self.cost_tracker.token_optimizer.optimize_prompt(prompt)
        
        if token_optimization["target_achieved"]:
            prompt = token_optimization["optimized_prompt"]
            optimization_result["optimizations_applied"].append("token_optimization")
            optimization_result["cost_analysis"]["token_savings"] = token_optimization["estimated_cost_savings"]
        
        # 3. Optimize model selection
        estimated_tokens = self.cost_tracker.token_optimizer.estimate_tokens(prompt)
        model_recommendation = self.cost_tracker.model_selector.recommend_model(
            task_type, 
            quality_threshold=0.8,
            budget_constraint=budget_constraint,
            estimated_tokens=estimated_tokens
        )
        
        if model_recommendation["recommended_model"] and model_recommendation["recommended_model"] != model:
            optimization_result["optimizations_applied"].append("model_optimization")
            optimization_result["recommendations"]["suggested_model"] = model_recommendation["recommended_model"]
            optimization_result["cost_analysis"]["model_savings"] = {
                "original_cost": self._estimate_cost(model, estimated_tokens),
                "optimized_cost": model_recommendation["estimated_cost"]
            }
        
        # 4. Calculate total potential savings
        total_savings = self._calculate_total_savings(optimization_result)
        optimization_result["cost_analysis"]["total_potential_savings"] = total_savings
        
        return optimization_result
    
    def _estimate_cost(self, model: str, tokens: int) -> float:
        """Estimate cost for model and token count"""
        model_costs = {
            "gpt-4o": 0.005,
            "gpt-4-turbo": 0.01,
            "gpt-3.5-turbo": 0.0015,
            "claude-3-5-sonnet-20241022": 0.003,
            "claude-3-haiku-20240307": 0.00025
        }
        
        cost_per_1k = model_costs.get(model, 0.005)  # Default cost
        return (tokens / 1000) * cost_per_1k
    
    def _calculate_total_savings(self, optimization_result: Dict[str, Any]) -> Dict[str, float]:
        """Calculate total potential savings from all optimizations"""
        total_savings = {
            "absolute_dollars": 0.0,
            "percentage": 0.0
        }
        
        cost_analysis = optimization_result.get("cost_analysis", {})
        
        # Token optimization savings
        if "token_savings" in cost_analysis:
            token_savings = cost_analysis["token_savings"]
            if isinstance(token_savings, dict) and "gpt-4" in token_savings:
                total_savings["absolute_dollars"] += float(token_savings["gpt-4"]["total_savings"])
        
        # Model optimization savings
        if "model_savings" in cost_analysis:
            model_savings = cost_analysis["model_savings"]
            if isinstance(model_savings, dict):
                original_cost = model_savings.get("original_cost", 0)
                optimized_cost = model_savings.get("optimized_cost", 0)
                total_savings["absolute_dollars"] += max(0, original_cost - optimized_cost)
        
        # Calculate percentage if we have original cost
        if "model_savings" in cost_analysis and total_savings["absolute_dollars"] > 0:
            original_cost = cost_analysis["model_savings"].get("original_cost", 0)
            if original_cost > 0:
                total_savings["percentage"] = (total_savings["absolute_dollars"] / original_cost) * 100
        
        return total_savings
    
    def generate_cost_optimization_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive cost optimization report"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get cost summary
        cost_summary = self.cost_tracker.get_cost_summary(start_date, end_date)
        
        # Get cache statistics
        cache_stats = self.cache.get_cache_stats()
        
        # Get prediction
        cost_prediction = self.cost_tracker.predict_monthly_cost()
        
        # Compile recommendations
        recommendations = []
        if "optimization_opportunities" in cost_summary:
            recommendations.extend(cost_summary["optimization_opportunities"])
        
        report = {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "current_costs": cost_summary,
            "cache_performance": cache_stats,
            "cost_predictions": cost_prediction,
            "optimization_recommendations": [asdict(rec) for rec in recommendations],
            "potential_savings_summary": self._calculate_potential_savings_summary(recommendations),
            "action_items": self._generate_action_items(recommendations)
        }
        
        return report
    
    def _calculate_potential_savings_summary(self, recommendations: List[OptimizationRecommendation]) -> Dict[str, Any]:
        """Calculate summary of potential savings from all recommendations"""
        if not recommendations:
            return {"total_savings": 0, "total_percentage": 0}
        
        total_savings = sum(rec.potential_savings_usd for rec in recommendations)
        avg_percentage = statistics.mean([rec.potential_savings_percentage for rec in recommendations])
        
        return {
            "total_potential_savings": float(total_savings),
            "average_percentage_savings": avg_percentage,
            "high_confidence_savings": float(sum(
                rec.potential_savings_usd for rec in recommendations 
                if rec.confidence_score > 0.8
            )),
            "quick_wins": len([rec for rec in recommendations if rec.implementation_effort == "low"]),
            "total_recommendations": len(recommendations)
        }
    
    def _generate_action_items(self, recommendations: List[OptimizationRecommendation]) -> List[Dict[str, Any]]:
        """Generate prioritized action items from recommendations"""
        # Sort recommendations by potential savings and confidence
        sorted_recs = sorted(
            recommendations,
            key=lambda x: float(x.potential_savings_usd) * x.confidence_score,
            reverse=True
        )
        
        action_items = []
        for i, rec in enumerate(sorted_recs[:5]):  # Top 5 recommendations
            action_items.append({
                "priority": i + 1,
                "title": rec.title,
                "potential_savings": float(rec.potential_savings_usd),
                "effort": rec.implementation_effort,
                "risk": rec.risk_level,
                "confidence": rec.confidence_score,
                "estimated_days": rec.estimated_impact_days,
                "first_step": rec.implementation_steps[0] if rec.implementation_steps else "Review recommendation details"
            })
        
        return action_items

# =============================================================================
# DEMONSTRATION FUNCTION
# =============================================================================

async def demonstrate_cost_optimization_system():
    """
    Comprehensive demonstration of the cost optimization system
    in realistic enterprise scenarios.
    """
    
    print(f"=== {__doc__.split('.')[0]} ===\n")
    
    # Initialize the cost optimization system
    optimizer = CostOptimizationSystem()
    
    print("1. Token Optimization")
    print("-" * 40)
    
    # Legal document analysis with verbose prompt (Lawstronaut scenario)
    verbose_prompt = """
    Please analyze the following legal contract clause in great detail and provide a comprehensive analysis including all potential risks, benefits, legal implications, precedents, and recommendations for modifications. The clause states: 'The party of the first part shall be liable for any and all damages whatsoever arising from any breach of this agreement, including but not limited to direct damages, indirect damages, consequential damages, punitive damages, and any other damages that may arise.' Please provide a thorough legal analysis.
    """
    
    token_result = optimizer.cost_tracker.token_optimizer.optimize_prompt(verbose_prompt, target_reduction=0.3)
    
    print(f"Original tokens: {token_result['original_tokens']}")
    print(f"Optimized tokens: {token_result['optimized_tokens']}")
    print(f"Reduction: {token_result['reduction_percentage']:.1%}")
    print(f"Optimized prompt: {token_result['optimized_prompt'][:200]}...")
    print()
    
    print("2. Model Selection Optimization")
    print("-" * 40)
    
    # Test different scenarios
    scenarios = [
        ("legal_analysis", 0.95, Decimal("0.10")),
        ("customer_service", 0.75, Decimal("0.02")),
        ("content_writing", 0.80, Decimal("0.05"))
    ]
    
    for task_type, quality_threshold, budget in scenarios:
        recommendation = optimizer.cost_tracker.model_selector.recommend_model(
            task_type, quality_threshold, budget, 1500
        )
        
        print(f"Task: {task_type}")
        print(f"Recommended model: {recommendation.get('recommended_model', 'None')}")
        if recommendation.get('recommended_model'):
            print(f"Quality score: {recommendation['quality_score']:.2f}")
            print(f"Estimated cost: ${recommendation['estimated_cost']:.4f}")
            print(f"Reason: {recommendation['reason']}")
        print()
    
    print("3. Comprehensive Request Optimization")
    print("-" * 40)
    
    # Optimize a customer service request (Optimizely scenario)
    customer_request = """
    Hello, I'm having trouble setting up A/B testing on my e-commerce website. I want to test different product page layouts to see which one converts better. Can you provide detailed step-by-step instructions for setting up A/B tests using your platform? I need to know about targeting, metrics, statistical significance, and best practices.
    """
    
    optimization_result = await optimizer.optimize_request(
        prompt=customer_request,
        model="gpt-4o",
        task_type="customer_service",
        budget_constraint=Decimal("0.05")
    )
    
    print("Optimization Result:")
    print(f"Optimizations applied: {optimization_result['optimizations_applied']}")
    if "recommendations" in optimization_result:
        recs = optimization_result["recommendations"]
        if "suggested_model" in recs:
            print(f"Suggested model: {recs['suggested_model']}")
    
    if "cost_analysis" in optimization_result:
        cost_analysis = optimization_result["cost_analysis"]
        if "total_potential_savings" in cost_analysis:
            savings = cost_analysis["total_potential_savings"]
            print(f"Potential savings: ${savings['absolute_dollars']:.4f} ({savings['percentage']:.1f}%)")
    print()
    
    print("4. Simulating Cost Metrics")
    print("-" * 40)
    
    # Simulate some cost metrics for demonstration
    import random
    
    models = ["gpt-4o", "gpt-3.5-turbo", "claude-3-5-sonnet-20241022"]
    applications = ["legal_analysis", "customer_service", "content_generation"]
    
    print("Recording sample cost metrics...")
    for i in range(50):
        model = random.choice(models)
        app = random.choice(applications)
        
        # Simulate realistic token counts and costs
        input_tokens = random.randint(500, 3000)
        output_tokens = random.randint(200, 1000)
        
        cost_per_token = {
            "gpt-4o": 0.000005,
            "gpt-3.5-turbo": 0.0000015,
            "claude-3-5-sonnet-20241022": 0.000003
        }
        
        total_cost = (input_tokens + output_tokens) * cost_per_token[model]
        
        metric = CostMetric(
            timestamp=datetime.utcnow() - timedelta(minutes=random.randint(0, 43200)),  # Last 30 days
            provider=model.split("-")[0] if "-" in model else model,
            model=model,
            operation_type="completion",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=Decimal(str(total_cost)),
            latency_ms=random.uniform(1000, 5000),
            application=app
        )
        
        optimizer.cost_tracker.record_cost(metric)
    
    print(f"Recorded {len(optimizer.cost_tracker.cost_metrics)} cost metrics")
    print()
    
    print("5. Cost Analysis and Reporting")
    print("-" * 40)
    
    # Generate cost summary
    cost_summary = optimizer.cost_tracker.get_cost_summary()
    
    print("Cost Summary (Last 30 days):")
    summary = cost_summary["summary"]
    print(f"Total cost: ${summary['total_cost']:.2f}")
    print(f"Total requests: {summary['total_requests']}")
    print(f"Average cost per request: ${summary['average_cost_per_request']:.4f}")
    
    print("\nCost breakdown by model:")
    for model, cost in cost_summary["breakdown"]["by_model"].items():
        print(f"  {model}: ${cost:.2f}")
    
    print("\nCost breakdown by application:")
    for app, cost in cost_summary["breakdown"]["by_application"].items():
        print(f"  {app}: ${cost:.2f}")
    
    # Show optimization recommendations
    if "optimization_opportunities" in cost_summary:
        print(f"\nOptimization opportunities found: {len(cost_summary['optimization_opportunities'])}")
        for rec in cost_summary["optimization_opportunities"][:2]:  # Show first 2
            print(f"  - {rec.title}")
            print(f"    Potential savings: ${rec.potential_savings_usd:.2f}")
            print(f"    Implementation effort: {rec.implementation_effort}")
    print()
    
    print("6. Monthly Cost Prediction")
    print("-" * 40)
    
    prediction = optimizer.cost_tracker.predict_monthly_cost()
    if "predicted_monthly_cost" in prediction:
        print(f"Predicted monthly cost: ${prediction['predicted_monthly_cost']:.2f}")
        if "confidence_interval" in prediction:
            ci = prediction["confidence_interval"]
            print(f"Confidence interval: ${ci['lower']:.2f} - ${ci['upper']:.2f}")
        print(f"Prediction confidence: {prediction.get('prediction_confidence', 'unknown')}")
    else:
        print(f"Prediction error: {prediction.get('error', 'Unknown error')}")
    print()
    
    print("7. Cache Performance")
    print("-" * 40)
    
    # Simulate some cache usage
    cache_stats = optimizer.cache.get_cache_stats()
    print(f"Cache size: {cache_stats['cache_size']} entries")
    print(f"Hit rate: {cache_stats['hit_rate']:.1%}")
    print(f"Total cost savings: ${cache_stats['total_cost_savings']:.2f}")
    print()
    
    print("8. Comprehensive Optimization Report")
    print("-" * 40)
    
    report = optimizer.generate_cost_optimization_report(days=7)
    
    print("Weekly Cost Optimization Report:")
    if "current_costs" in report and "summary" in report["current_costs"]:
        summary = report["current_costs"]["summary"]
        print(f"Week total cost: ${summary['total_cost']:.2f}")
        print(f"Total requests: {summary['total_requests']}")
    
    if "potential_savings_summary" in report:
        savings = report["potential_savings_summary"]
        print(f"\nPotential savings: ${savings['total_potential_savings']:.2f}")
        print(f"Average savings percentage: {savings['average_percentage_savings']:.1f}%")
        print(f"Quick wins available: {savings['quick_wins']}")
    
    if "action_items" in report and report["action_items"]:
        print("\nTop action items:")
        for item in report["action_items"][:3]:
            print(f"  {item['priority']}. {item['title']}")
            print(f"     Savings: ${item['potential_savings']:.2f}, Effort: {item['effort']}")
    
    print("\n=== Cost optimization system demonstration completed ===")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run demonstration
    asyncio.run(demonstrate_cost_optimization_system())