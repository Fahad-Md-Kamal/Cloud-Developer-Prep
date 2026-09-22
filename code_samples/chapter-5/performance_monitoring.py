"""
Comprehensive Performance Monitoring and Alerting System

This module implements a production-ready performance monitoring system with
real-time metrics collection, alerting, and dashboards for enterprise applications.
Designed for systems like Lawstronaut (legal document processing) and Optimizely
(personalization engines) handling millions of requests.

Key features:
- Real-time system and application metrics collection
- Intelligent alerting with escalation policies
- Performance profiling and bottleneck detection
- Custom business metrics tracking
- Integration with monitoring platforms (Grafana, Prometheus)

Author: Technical Interview Preparation Guide
"""

import asyncio
import json
import logging
import statistics
import time
import threading
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from contextlib import asynccontextmanager
import psutil
import queue
import weakref

# =============================================================================
# METRICS COLLECTION SYSTEM
# =============================================================================

@dataclass
class MetricPoint:
    """Individual metric measurement"""
    name: str
    value: Union[int, float]
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"  # gauge, counter, histogram, timer

@dataclass 
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric_name: str
    condition: str  # "gt", "lt", "eq"
    threshold: Union[int, float]
    evaluation_period: int  # seconds
    severity: str  # "warning", "critical"
    notification_channels: List[str] = field(default_factory=list)

class MetricCollector(ABC):
    """Abstract base class for metric collectors"""
    
    @abstractmethod
    async def collect_metrics(self) -> List[MetricPoint]:
        """Collect and return metrics"""
        pass
    
    @abstractmethod
    def get_collector_name(self) -> str:
        """Get collector name"""
        pass

class SystemMetricsCollector(MetricCollector):
    """System-level metrics collector"""
    
    def __init__(self):
        self._process = psutil.Process()
    
    async def collect_metrics(self) -> List[MetricPoint]:
        """Collect system performance metrics"""
        current_time = time.time()
        metrics = []
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        metrics.append(MetricPoint(
            name="system.cpu.usage_percent",
            value=cpu_percent,
            timestamp=current_time,
            tags={"host": "localhost"},
            metric_type="gauge"
        ))
        
        # Memory metrics
        memory = psutil.virtual_memory()
        metrics.extend([
            MetricPoint("system.memory.usage_percent", memory.percent, current_time,
                       {"host": "localhost"}, "gauge"),
            MetricPoint("system.memory.available_gb", memory.available / (1024**3), current_time,
                       {"host": "localhost"}, "gauge"),
            MetricPoint("system.memory.used_gb", memory.used / (1024**3), current_time,
                       {"host": "localhost"}, "gauge")
        ])
        
        # Disk I/O metrics
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                metrics.extend([
                    MetricPoint("system.disk.read_bytes_per_sec", disk_io.read_bytes, current_time,
                               {"host": "localhost"}, "counter"),
                    MetricPoint("system.disk.write_bytes_per_sec", disk_io.write_bytes, current_time,
                               {"host": "localhost"}, "counter")
                ])
        except:
            pass
        
        # Network I/O metrics
        try:
            network_io = psutil.net_io_counters()
            if network_io:
                metrics.extend([
                    MetricPoint("system.network.bytes_sent_per_sec", network_io.bytes_sent, current_time,
                               {"host": "localhost"}, "counter"),
                    MetricPoint("system.network.bytes_recv_per_sec", network_io.bytes_recv, current_time,
                               {"host": "localhost"}, "counter")
                ])
        except:
            pass
        
        # Process-specific metrics
        try:
            process_memory = self._process.memory_info()
            process_cpu = self._process.cpu_percent()
            
            metrics.extend([
                MetricPoint("process.memory.rss_mb", process_memory.rss / (1024**2), current_time,
                           {"process": "application"}, "gauge"),
                MetricPoint("process.memory.vms_mb", process_memory.vms / (1024**2), current_time,
                           {"process": "application"}, "gauge"),
                MetricPoint("process.cpu.usage_percent", process_cpu, current_time,
                           {"process": "application"}, "gauge"),
                MetricPoint("process.threads.count", self._process.num_threads(), current_time,
                           {"process": "application"}, "gauge")
            ])
        except:
            pass
        
        return metrics
    
    def get_collector_name(self) -> str:
        return "system_metrics"

class ApplicationMetricsCollector(MetricCollector):
    """Application-level metrics collector"""
    
    def __init__(self):
        self._request_counts = {}
        self._response_times = []
        self._error_counts = {}
        self._custom_metrics = {}
        self._lock = threading.RLock()
    
    def record_request(self, endpoint: str, response_time_ms: float, status_code: int):
        """Record HTTP request metrics"""
        with self._lock:
            # Request count
            self._request_counts[endpoint] = self._request_counts.get(endpoint, 0) + 1
            
            # Response time
            self._response_times.append(response_time_ms)
            
            # Keep only recent response times (last 1000)
            if len(self._response_times) > 1000:
                self._response_times = self._response_times[-1000:]
            
            # Error count
            if status_code >= 400:
                error_key = f"{endpoint}_{status_code}"
                self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
    
    def record_custom_metric(self, name: str, value: Union[int, float], tags: Dict[str, str] = None):
        """Record custom application metric"""
        with self._lock:
            metric_key = f"{name}_{json.dumps(tags or {}, sort_keys=True)}"
            
            if metric_key not in self._custom_metrics:
                self._custom_metrics[metric_key] = []
            
            self._custom_metrics[metric_key].append(value)
            
            # Keep only recent values
            if len(self._custom_metrics[metric_key]) > 100:
                self._custom_metrics[metric_key] = self._custom_metrics[metric_key][-100:]
    
    async def collect_metrics(self) -> List[MetricPoint]:
        """Collect application performance metrics"""
        current_time = time.time()
        metrics = []
        
        with self._lock:
            # Request rate metrics
            total_requests = sum(self._request_counts.values())
            metrics.append(MetricPoint(
                name="application.requests.total",
                value=total_requests,
                timestamp=current_time,
                metric_type="counter"
            ))
            
            # Request rate by endpoint
            for endpoint, count in self._request_counts.items():
                metrics.append(MetricPoint(
                    name="application.requests.by_endpoint",
                    value=count,
                    timestamp=current_time,
                    tags={"endpoint": endpoint},
                    metric_type="counter"
                ))
            
            # Response time metrics
            if self._response_times:
                metrics.extend([
                    MetricPoint("application.response_time.avg_ms", 
                               statistics.mean(self._response_times), current_time, metric_type="gauge"),
                    MetricPoint("application.response_time.median_ms",
                               statistics.median(self._response_times), current_time, metric_type="gauge"),
                    MetricPoint("application.response_time.p95_ms",
                               self._percentile(self._response_times, 95), current_time, metric_type="gauge"),
                    MetricPoint("application.response_time.p99_ms",
                               self._percentile(self._response_times, 99), current_time, metric_type="gauge")
                ])
            
            # Error rate metrics
            total_errors = sum(self._error_counts.values())
            if total_requests > 0:
                error_rate = total_errors / total_requests
                metrics.append(MetricPoint(
                    name="application.error_rate",
                    value=error_rate,
                    timestamp=current_time,
                    metric_type="gauge"
                ))
            
            # Custom metrics
            for metric_key, values in self._custom_metrics.items():
                if values:
                    # Extract name and tags from key
                    parts = metric_key.split('_', 1)
                    if len(parts) == 2:
                        name, tags_json = parts
                        try:
                            tags = json.loads(tags_json) if tags_json != '{}' else {}
                        except:
                            tags = {}
                    else:
                        name = metric_key
                        tags = {}
                    
                    metrics.append(MetricPoint(
                        name=f"application.custom.{name}",
                        value=statistics.mean(values),
                        timestamp=current_time,
                        tags=tags,
                        metric_type="gauge"
                    ))
        
        return metrics
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = (percentile / 100.0) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = int(index)
            upper = lower + 1
            weight = index - lower
            
            if upper >= len(sorted_data):
                return sorted_data[lower]
            
            return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight
    
    def get_collector_name(self) -> str:
        return "application_metrics"

# =============================================================================
# ALERTING SYSTEM
# =============================================================================

class AlertEvaluator:
    """Evaluates alert conditions and triggers notifications"""
    
    def __init__(self):
        self.alert_rules: Dict[str, AlertRule] = {}
        self.metric_history: Dict[str, List[MetricPoint]] = {}
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def add_alert_rule(self, rule: AlertRule):
        """Add alert rule"""
        with self._lock:
            self.alert_rules[rule.name] = rule
    
    def evaluate_alerts(self, metrics: List[MetricPoint]) -> List[Dict[str, Any]]:
        """Evaluate alert conditions against metrics"""
        triggered_alerts = []
        
        with self._lock:
            # Update metric history
            for metric in metrics:
                if metric.name not in self.metric_history:
                    self.metric_history[metric.name] = []
                
                self.metric_history[metric.name].append(metric)
                
                # Keep only recent history (last 1 hour)
                cutoff_time = time.time() - 3600
                self.metric_history[metric.name] = [
                    m for m in self.metric_history[metric.name]
                    if m.timestamp > cutoff_time
                ]
            
            # Evaluate each alert rule
            for rule_name, rule in self.alert_rules.items():
                alert_result = self._evaluate_rule(rule)
                
                if alert_result['is_triggered']:
                    if rule_name not in self.active_alerts:
                        # New alert
                        self.active_alerts[rule_name] = {
                            'rule': rule,
                            'first_triggered': time.time(),
                            'last_triggered': time.time(),
                            'trigger_count': 1
                        }
                        
                        triggered_alerts.append({
                            'rule_name': rule_name,
                            'severity': rule.severity,
                            'message': alert_result['message'],
                            'metric_value': alert_result['metric_value'],
                            'threshold': rule.threshold,
                            'is_new': True
                        })
                    else:
                        # Existing alert - update
                        self.active_alerts[rule_name]['last_triggered'] = time.time()
                        self.active_alerts[rule_name]['trigger_count'] += 1
                else:
                    if rule_name in self.active_alerts:
                        # Alert resolved
                        triggered_alerts.append({
                            'rule_name': rule_name,
                            'severity': 'resolved',
                            'message': f"Alert {rule_name} has been resolved",
                            'metric_value': alert_result['metric_value'],
                            'threshold': rule.threshold,
                            'is_resolved': True,
                            'duration': time.time() - self.active_alerts[rule_name]['first_triggered']
                        })
                        
                        del self.active_alerts[rule_name]
        
        return triggered_alerts
    
    def _evaluate_rule(self, rule: AlertRule) -> Dict[str, Any]:
        """Evaluate individual alert rule"""
        if rule.metric_name not in self.metric_history:
            return {'is_triggered': False, 'message': 'No data', 'metric_value': None}
        
        # Get recent metrics within evaluation period
        cutoff_time = time.time() - rule.evaluation_period
        recent_metrics = [
            m for m in self.metric_history[rule.metric_name]
            if m.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {'is_triggered': False, 'message': 'No recent data', 'metric_value': None}
        
        # Calculate aggregate value (using average for simplicity)
        metric_values = [m.value for m in recent_metrics]
        current_value = statistics.mean(metric_values)
        
        # Evaluate condition
        is_triggered = False
        if rule.condition == "gt" and current_value > rule.threshold:
            is_triggered = True
        elif rule.condition == "lt" and current_value < rule.threshold:
            is_triggered = True
        elif rule.condition == "eq" and current_value == rule.threshold:
            is_triggered = True
        
        message = f"{rule.metric_name} is {current_value:.2f} (threshold: {rule.threshold})"
        
        return {
            'is_triggered': is_triggered,
            'message': message,
            'metric_value': current_value
        }
    
    def get_active_alerts(self) -> Dict[str, Any]:
        """Get currently active alerts"""
        with self._lock:
            return {
                'active_count': len(self.active_alerts),
                'alerts': [
                    {
                        'rule_name': name,
                        'severity': alert_data['rule'].severity,
                        'duration': time.time() - alert_data['first_triggered'],
                        'trigger_count': alert_data['trigger_count']
                    }
                    for name, alert_data in self.active_alerts.items()
                ]
            }

class NotificationManager:
    """Manages alert notifications across multiple channels"""
    
    def __init__(self):
        self.notification_channels: Dict[str, Callable] = {}
        self._notification_history = []
        self._lock = threading.RLock()
    
    def register_channel(self, channel_name: str, handler: Callable):
        """Register notification channel"""
        self.notification_channels[channel_name] = handler
    
    async def send_notification(self, alert: Dict[str, Any]) -> bool:
        """Send alert notification"""
        with self._lock:
            # Record notification
            notification_record = {
                'alert': alert,
                'timestamp': time.time(),
                'channels_notified': []
            }
            
            # Send to configured channels
            success = False
            for channel_name, handler in self.notification_channels.items():
                try:
                    await handler(alert)
                    notification_record['channels_notified'].append(channel_name)
                    success = True
                except Exception as e:
                    logging.error(f"Failed to send notification via {channel_name}: {e}")
            
            self._notification_history.append(notification_record)
            
            # Keep only recent history (last 1000 notifications)
            if len(self._notification_history) > 1000:
                self._notification_history = self._notification_history[-1000:]
            
            return success
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        with self._lock:
            if not self._notification_history:
                return {'total_notifications': 0}
            
            total_notifications = len(self._notification_history)
            
            # Channel success rates
            channel_stats = {}
            for record in self._notification_history:
                for channel in record['channels_notified']:
                    if channel not in channel_stats:
                        channel_stats[channel] = {'sent': 0, 'total': 0}
                    channel_stats[channel]['sent'] += 1
                
                for channel in self.notification_channels.keys():
                    if channel not in channel_stats:
                        channel_stats[channel] = {'sent': 0, 'total': 0}
                    channel_stats[channel]['total'] += 1
            
            return {
                'total_notifications': total_notifications,
                'registered_channels': list(self.notification_channels.keys()),
                'channel_success_rates': {
                    channel: stats['sent'] / stats['total'] if stats['total'] > 0 else 0
                    for channel, stats in channel_stats.items()
                }
            }

# =============================================================================
# PERFORMANCE MONITORING SYSTEM
# =============================================================================

class PerformanceMonitor:
    """Main performance monitoring system"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.collectors: List[MetricCollector] = []
        self.alert_evaluator = AlertEvaluator()
        self.notification_manager = NotificationManager()
        
        self.metrics_buffer: List[MetricPoint] = []
        self.monitoring_active = False
        self.monitoring_task = None
        
        self._config = self._load_config(config_file)
        self._setup_default_collectors()
        self._setup_default_alert_rules()
        self._setup_notification_channels()
        
        self._lock = threading.RLock()
    
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load monitoring configuration"""
        default_config = {
            'monitoring': {
                'interval_seconds': 30,
                'retention_days': 7
            },
            'alerts': {
                'cpu_usage': {'threshold': 80, 'severity': 'warning'},
                'memory_usage': {'threshold': 90, 'severity': 'critical'},
                'response_time': {'threshold': 1000, 'severity': 'warning'}
            }
        }
        
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                        loaded_config = yaml.safe_load(f)
                    else:
                        loaded_config = json.load(f)
                
                # Merge with defaults
                default_config.update(loaded_config)
            except Exception as e:
                logging.error(f"Failed to load config file {config_file}: {e}")
        
        return default_config
    
    def _setup_default_collectors(self):
        """Setup default metric collectors"""
        self.add_collector(SystemMetricsCollector())
        self.add_collector(ApplicationMetricsCollector())
    
    def _setup_default_alert_rules(self):
        """Setup default alert rules"""
        alert_configs = self._config.get('alerts', {})
        
        # CPU usage alert
        if 'cpu_usage' in alert_configs:
            config = alert_configs['cpu_usage']
            self.alert_evaluator.add_alert_rule(AlertRule(
                name="high_cpu_usage",
                metric_name="system.cpu.usage_percent",
                condition="gt",
                threshold=config.get('threshold', 80),
                evaluation_period=300,
                severity=config.get('severity', 'warning')
            ))
        
        # Memory usage alert
        if 'memory_usage' in alert_configs:
            config = alert_configs['memory_usage']
            self.alert_evaluator.add_alert_rule(AlertRule(
                name="high_memory_usage",
                metric_name="system.memory.usage_percent", 
                condition="gt",
                threshold=config.get('threshold', 90),
                evaluation_period=300,
                severity=config.get('severity', 'critical')
            ))
        
        # Response time alert
        if 'response_time' in alert_configs:
            config = alert_configs['response_time']
            self.alert_evaluator.add_alert_rule(AlertRule(
                name="high_response_time",
                metric_name="application.response_time.avg_ms",
                condition="gt",
                threshold=config.get('threshold', 1000),
                evaluation_period=180,
                severity=config.get('severity', 'warning')
            ))
    
    def _setup_notification_channels(self):
        """Setup notification channels"""
        # Console notification handler
        async def console_handler(alert: Dict[str, Any]):
            severity = alert.get('severity', 'info').upper()
            message = alert.get('message', 'No message')
            print(f"[{severity}] ALERT: {alert.get('rule_name', 'Unknown')} - {message}")
        
        # Email notification handler (mock)
        async def email_handler(alert: Dict[str, Any]):
            logging.info(f"Email sent for alert: {alert.get('rule_name')}")
        
        # Slack notification handler (mock)
        async def slack_handler(alert: Dict[str, Any]):
            logging.info(f"Slack notification sent for alert: {alert.get('rule_name')}")
        
        self.notification_manager.register_channel('console', console_handler)
        self.notification_manager.register_channel('email', email_handler)
        self.notification_manager.register_channel('slack', slack_handler)
    
    def add_collector(self, collector: MetricCollector):
        """Add metric collector"""
        self.collectors.append(collector)
    
    def add_alert_rule(self, rule: AlertRule):
        """Add custom alert rule"""
        self.alert_evaluator.add_alert_rule(rule)
    
    async def start_monitoring(self):
        """Start performance monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        interval = self._config.get('monitoring', {}).get('interval_seconds', 30)
        
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval)
        )
        
        logging.info(f"Performance monitoring started with {interval}s interval")
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logging.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self, interval: int):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect metrics from all collectors
                all_metrics = []
                
                for collector in self.collectors:
                    try:
                        metrics = await collector.collect_metrics()
                        all_metrics.extend(metrics)
                    except Exception as e:
                        logging.error(f"Error collecting metrics from {collector.get_collector_name()}: {e}")
                
                # Store metrics
                with self._lock:
                    self.metrics_buffer.extend(all_metrics)
                    
                    # Keep buffer size manageable
                    if len(self.metrics_buffer) > 10000:
                        self.metrics_buffer = self.metrics_buffer[-5000:]
                
                # Evaluate alerts
                triggered_alerts = self.alert_evaluator.evaluate_alerts(all_metrics)
                
                # Send notifications for triggered alerts
                for alert in triggered_alerts:
                    await self.notification_manager.send_notification(alert)
                
                logging.debug(f"Collected {len(all_metrics)} metrics, {len(triggered_alerts)} alerts triggered")
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    def record_request_metric(self, endpoint: str, response_time_ms: float, status_code: int):
        """Record HTTP request metric"""
        for collector in self.collectors:
            if isinstance(collector, ApplicationMetricsCollector):
                collector.record_request(endpoint, response_time_ms, status_code)
                break
    
    def record_custom_metric(self, name: str, value: Union[int, float], tags: Dict[str, str] = None):
        """Record custom application metric"""
        for collector in self.collectors:
            if isinstance(collector, ApplicationMetricsCollector):
                collector.record_custom_metric(name, value, tags)
                break
    
    def get_current_metrics(self, metric_name: Optional[str] = None) -> List[MetricPoint]:
        """Get current metrics"""
        with self._lock:
            if metric_name:
                return [m for m in self.metrics_buffer if m.name == metric_name]
            return self.metrics_buffer.copy()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance monitoring summary"""
        with self._lock:
            recent_metrics = [
                m for m in self.metrics_buffer
                if m.timestamp > time.time() - 300  # Last 5 minutes
            ]
            
            # Group metrics by name
            metric_groups = {}
            for metric in recent_metrics:
                if metric.name not in metric_groups:
                    metric_groups[metric.name] = []
                metric_groups[metric.name].append(metric.value)
            
            # Calculate summaries
            metric_summaries = {}
            for name, values in metric_groups.items():
                if values:
                    metric_summaries[name] = {
                        'current': values[-1],
                        'avg': statistics.mean(values),
                        'min': min(values),
                        'max': max(values),
                        'count': len(values)
                    }
            
            active_alerts = self.alert_evaluator.get_active_alerts()
            notification_stats = self.notification_manager.get_notification_stats()
            
            return {
                'monitoring_status': 'active' if self.monitoring_active else 'stopped',
                'collectors_count': len(self.collectors),
                'metrics_collected': len(self.metrics_buffer),
                'recent_metrics_count': len(recent_metrics),
                'metric_summaries': metric_summaries,
                'active_alerts': active_alerts,
                'notification_stats': notification_stats
            }

# =============================================================================
# ENTERPRISE-SPECIFIC MONITORS
# =============================================================================

class LegalDocumentMonitor:
    """Specialized monitoring for legal document processing (Lawstronaut)"""
    
    def __init__(self, performance_monitor: PerformanceMonitor):
        self.monitor = performance_monitor
        self._setup_legal_alerts()
    
    def _setup_legal_alerts(self):
        """Setup legal document specific alerts"""
        # Document processing time alert
        self.monitor.add_alert_rule(AlertRule(
            name="slow_document_processing",
            metric_name="application.custom.document_processing_time",
            condition="gt",
            threshold=5000,  # 5 seconds
            evaluation_period=300,
            severity="warning"
        ))
        
        # Document classification accuracy alert
        self.monitor.add_alert_rule(AlertRule(
            name="low_classification_accuracy",
            metric_name="application.custom.classification_accuracy",
            condition="lt",
            threshold=0.90,  # 90% accuracy
            evaluation_period=600,
            severity="critical"
        ))
        
        # Legal term extraction rate alert
        self.monitor.add_alert_rule(AlertRule(
            name="low_term_extraction_rate",
            metric_name="application.custom.legal_terms_extracted_per_min",
            condition="lt", 
            threshold=100,
            evaluation_period=300,
            severity="warning"
        ))
    
    def record_document_processed(self, document_id: str, processing_time_ms: float, 
                                 terms_extracted: int, classification_confidence: float):
        """Record document processing metrics"""
        self.monitor.record_custom_metric("document_processing_time", processing_time_ms,
                                        {"document_id": document_id})
        self.monitor.record_custom_metric("legal_terms_extracted", terms_extracted,
                                        {"document_id": document_id})
        self.monitor.record_custom_metric("classification_confidence", classification_confidence,
                                        {"document_id": document_id})
    
    def record_search_performance(self, query: str, results_count: int, search_time_ms: float):
        """Record search performance metrics"""
        self.monitor.record_custom_metric("search_time", search_time_ms,
                                        {"query_type": "legal_search"})
        self.monitor.record_custom_metric("search_results_count", results_count,
                                        {"query_type": "legal_search"})

class PersonalizationMonitor:
    """Specialized monitoring for personalization engine (Optimizely)"""
    
    def __init__(self, performance_monitor: PerformanceMonitor):
        self.monitor = performance_monitor
        self._setup_personalization_alerts()
    
    def _setup_personalization_alerts(self):
        """Setup personalization specific alerts"""
        # Recommendation generation time alert
        self.monitor.add_alert_rule(AlertRule(
            name="slow_recommendation_generation",
            metric_name="application.custom.recommendation_time",
            condition="gt",
            threshold=500,  # 500ms
            evaluation_period=180,
            severity="warning"
        ))
        
        # A/B test conversion rate alert
        self.monitor.add_alert_rule(AlertRule(
            name="low_conversion_rate",
            metric_name="application.custom.conversion_rate",
            condition="lt",
            threshold=0.05,  # 5% conversion rate
            evaluation_period=900,  # 15 minutes
            severity="warning"
        ))
        
        # Real-time feature response time alert
        self.monitor.add_alert_rule(AlertRule(
            name="slow_feature_response",
            metric_name="application.custom.feature_response_time",
            condition="gt",
            threshold=100,  # 100ms
            evaluation_period=120,
            severity="critical"
        ))
    
    def record_recommendation_generated(self, user_id: str, recommendation_count: int, 
                                      generation_time_ms: float, accuracy_score: float):
        """Record recommendation generation metrics"""
        self.monitor.record_custom_metric("recommendation_time", generation_time_ms,
                                        {"user_id": user_id})
        self.monitor.record_custom_metric("recommendation_count", recommendation_count,
                                        {"user_id": user_id})
        self.monitor.record_custom_metric("recommendation_accuracy", accuracy_score,
                                        {"user_id": user_id})
    
    def record_ab_test_result(self, test_id: str, variant: str, converted: bool, 
                             user_engagement_time: float):
        """Record A/B test performance metrics"""
        conversion_value = 1.0 if converted else 0.0
        
        self.monitor.record_custom_metric("conversion_rate", conversion_value,
                                        {"test_id": test_id, "variant": variant})
        self.monitor.record_custom_metric("engagement_time", user_engagement_time,
                                        {"test_id": test_id, "variant": variant})

# =============================================================================
# DEMONSTRATION
# =============================================================================

async def demonstrate_performance_monitoring():
    """Comprehensive demonstration of performance monitoring system"""
    
    print("=== Performance Monitoring and Alerting Demo ===\n")
    
    # Initialize performance monitor
    monitor = PerformanceMonitor()
    
    # Initialize enterprise-specific monitors
    legal_monitor = LegalDocumentMonitor(monitor)
    personalization_monitor = PersonalizationMonitor(monitor)
    
    print("1. Performance Monitor Initialization")
    print("-" * 50)
    print(f"Monitoring system initialized with {len(monitor.collectors)} collectors")
    print(f"Alert rules configured: {len(monitor.alert_evaluator.alert_rules)}")
    print(f"Notification channels: {len(monitor.notification_manager.notification_channels)}")
    
    # Start monitoring
    await monitor.start_monitoring()
    print("Performance monitoring started")
    
    print("\n2. Simulating Application Load")
    print("-" * 50)
    
    # Simulate HTTP requests
    endpoints = ["/api/documents", "/api/search", "/api/recommendations", "/api/profiles"]
    
    for i in range(50):
        endpoint = endpoints[i % len(endpoints)]
        response_time = 50 + (i * 10)  # Gradually increasing response time
        status_code = 200 if i % 10 != 0 else 500  # 10% error rate
        
        monitor.record_request_metric(endpoint, response_time, status_code)
        
        # Simulate some processing delay
        await asyncio.sleep(0.01)
    
    print(f"Simulated {50} HTTP requests across {len(endpoints)} endpoints")
    
    print("\n3. Legal Document Processing Simulation")
    print("-" * 50)
    
    # Simulate legal document processing
    for i in range(20):
        doc_id = f"legal_doc_{i}"
        processing_time = 1000 + (i * 100)  # Increasing processing time
        terms_extracted = max(5, 20 - i)  # Decreasing extraction rate
        classification_confidence = max(0.6, 0.95 - (i * 0.01))  # Decreasing accuracy
        
        legal_monitor.record_document_processed(
            doc_id, processing_time, terms_extracted, classification_confidence
        )
        
        # Simulate search operations
        search_time = 100 + (i * 5)
        results_count = max(10, 50 - i)
        
        legal_monitor.record_search_performance(
            f"query_{i}", results_count, search_time
        )
    
    print("Simulated legal document processing and search operations")
    
    print("\n4. Personalization Engine Simulation") 
    print("-" * 50)
    
    # Simulate personalization operations
    for i in range(30):
        user_id = f"user_{i}"
        recommendation_time = 200 + (i * 15)  # Increasing response time
        recommendation_count = 10
        accuracy_score = max(0.7, 0.95 - (i * 0.005))
        
        personalization_monitor.record_recommendation_generated(
            user_id, recommendation_count, recommendation_time, accuracy_score
        )
        
        # Simulate A/B test results
        test_id = f"test_{i % 3}"
        variant = "A" if i % 2 == 0 else "B"
        converted = i % 8 == 0  # ~12.5% conversion rate
        engagement_time = 30 + (i * 2)
        
        personalization_monitor.record_ab_test_result(
            test_id, variant, converted, engagement_time
        )
    
    print("Simulated personalization and A/B testing operations")
    
    print("\n5. Waiting for Metrics Collection and Alert Evaluation")
    print("-" * 50)
    
    # Wait for monitoring cycle to complete
    await asyncio.sleep(35)  # Wait longer than monitoring interval
    
    print("\n6. Performance Summary Analysis")
    print("-" * 50)
    
    # Get performance summary
    summary = monitor.get_performance_summary()
    
    print("Performance Monitoring Status:")
    print(f"  Status: {summary['monitoring_status']}")
    print(f"  Collectors: {summary['collectors_count']}")
    print(f"  Total metrics collected: {summary['metrics_collected']}")
    print(f"  Recent metrics (5min): {summary['recent_metrics_count']}")
    
    # Show key metrics
    print("\nKey Performance Metrics:")
    metric_summaries = summary.get('metric_summaries', {})
    
    for metric_name, stats in list(metric_summaries.items())[:10]:  # Show top 10
        print(f"  {metric_name}:")
        print(f"    Current: {stats['current']:.2f}")
        print(f"    Average: {stats['avg']:.2f}")
        print(f"    Range: {stats['min']:.2f} - {stats['max']:.2f}")
    
    # Show active alerts
    print("\nActive Alerts:")
    active_alerts = summary.get('active_alerts', {})
    if active_alerts['active_count'] > 0:
        for alert in active_alerts['alerts']:
            print(f"  - {alert['rule_name']} ({alert['severity']}) - Duration: {alert['duration']:.1f}s")
    else:
        print("  No active alerts")
    
    # Show notification statistics
    print("\nNotification Statistics:")
    notification_stats = summary.get('notification_stats', {})
    print(f"  Total notifications sent: {notification_stats.get('total_notifications', 0)}")
    
    channel_success_rates = notification_stats.get('channel_success_rates', {})
    for channel, success_rate in channel_success_rates.items():
        print(f"  {channel} success rate: {success_rate:.1%}")
    
    print("\n7. Custom Metrics Analysis")
    print("-" * 50)
    
    # Analyze custom metrics
    custom_metrics = monitor.get_current_metrics()
    
    # Group by custom metrics
    custom_metric_names = set(
        m.name for m in custom_metrics 
        if m.name.startswith('application.custom.')
    )
    
    print("Custom Business Metrics:")
    for metric_name in sorted(custom_metric_names):
        recent_values = [
            m.value for m in custom_metrics
            if m.name == metric_name and m.timestamp > time.time() - 300
        ]
        
        if recent_values:
            avg_value = statistics.mean(recent_values)
            print(f"  {metric_name.replace('application.custom.', '')}: {avg_value:.2f} (avg)")
    
    print("\n8. Performance Optimization Recommendations")
    print("-" * 50)
    
    # Analyze performance and provide recommendations
    recommendations = []
    
    # Check response times
    response_time_metrics = [
        m for m in custom_metrics 
        if 'response_time' in m.name or 'processing_time' in m.name
    ]
    
    if response_time_metrics:
        avg_response_time = statistics.mean([m.value for m in response_time_metrics])
        if avg_response_time > 1000:
            recommendations.append(
                "High response times detected. Consider implementing caching or query optimization."
            )
    
    # Check error rates
    error_metrics = [m for m in custom_metrics if 'error' in m.name]
    if error_metrics:
        recommendations.append(
            "Monitor error rates closely and implement circuit breakers for resilience."
        )
    
    # Check resource utilization
    cpu_metrics = [m for m in custom_metrics if 'cpu' in m.name]
    if cpu_metrics:
        avg_cpu = statistics.mean([m.value for m in cpu_metrics])
        if avg_cpu > 70:
            recommendations.append(
                "High CPU utilization detected. Consider horizontal scaling or performance optimization."
            )
    
    print("Performance Optimization Recommendations:")
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
    else:
        print("  System performance is within acceptable parameters")
    
    # Stop monitoring
    await monitor.stop_monitoring()
    
    print("\n=== Performance Monitoring Demo Completed ===")
    
    print("\nKey Monitoring Insights:")
    print("- Real-time metrics collection enables proactive performance management")
    print("- Intelligent alerting prevents issues from becoming critical problems")
    print("- Custom business metrics provide domain-specific performance visibility")
    print("- Multi-channel notifications ensure alerts reach the right teams quickly")
    print("- Performance trends help identify optimization opportunities")
    print("- Enterprise-specific monitors enable targeted performance management")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the comprehensive performance monitoring demonstration
    asyncio.run(demonstrate_performance_monitoring())