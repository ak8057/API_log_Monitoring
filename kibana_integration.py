import json
import requests
import logging
import os
from datetime import datetime
import uuid
import time
from typing import Dict, List, Any, Optional

class KibanaRootCauseIntegration:
    """
    Integration class for sending API root cause analysis data to Elasticsearch/Kibana
    """
    def __init__(self, 
                 es_host: str = 'http://localhost:9200',
                 es_username: str = 'elastic',
                 es_password: Optional[str] = None,
                 index_prefix: str = 'api-monitoring',
                 dashboard_name: str = 'API Root Cause Analysis',
                 create_visualizations: bool = True):
        """
        Initialize Kibana integration
        
        Args:
            es_host: Elasticsearch host URL
            es_username: Elasticsearch username
            es_password: Elasticsearch password
            index_prefix: Prefix for Elasticsearch indices
            dashboard_name: Name of the Kibana dashboard to create
            create_visualizations: Whether to create Kibana visualizations
        """
        self.es_host = es_host
        self.es_username = es_username
        self.es_password = es_password or self._read_es_password()
        self.index_prefix = index_prefix
        self.dashboard_name = dashboard_name
        self.create_visualizations = create_visualizations
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('kibana_integration')
        
        # Configure indices
        self.error_patterns_index = f"{index_prefix}-error-patterns"
        self.response_time_index = f"{index_prefix}-response-times"
        self.insights_index = f"{index_prefix}-insights"
        self.recommendations_index = f"{index_prefix}-recommendations"
        self.health_check_index = f"{index_prefix}-health-checks"
        
        # Initialize session
        self.session = requests.Session()
        self.session.auth = (self.es_username, self.es_password)
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def _read_es_password(self) -> str:
        """
        Read Elasticsearch password from .env file or environment variable
        
        Returns:
            Elasticsearch password
        """
        # Try to read from .env file
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('ES_LOCAL_PASSWORD='):
                        return line.split('=', 1)[1].strip().strip('"\'')
        
        # Try to read from environment variable
        if 'ES_LOCAL_PASSWORD' in os.environ:
            return os.environ['ES_LOCAL_PASSWORD']
        
        # Return empty string if password not found
        return ""
    
    def create_indices(self) -> bool:
        """
        Create Elasticsearch indices for root cause analysis data
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Creating Elasticsearch indices with prefix: {self.index_prefix}")
        
        indices_settings = {
            self.error_patterns_index: {
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "error_type": {"type": "keyword"},
                        "endpoint": {"type": "keyword"},
                        "method": {"type": "keyword"},
                        "count": {"type": "integer"},
                        "percentage": {"type": "float"},
                        "messages": {"type": "text"},
                        "status_codes": {"type": "integer"}
                    }
                }
            },
            self.response_time_index: {
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "endpoint": {"type": "keyword"},
                        "method": {"type": "keyword"},
                        "avg_response_time": {"type": "float"},
                        "max_response_time": {"type": "float"},
                        "min_response_time": {"type": "float"},
                        "count": {"type": "integer"},
                        "cluster_id": {"type": "keyword"}
                    }
                }
            },
            self.insights_index: {
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "insight": {"type": "text"},
                        "category": {"type": "keyword"},
                        "severity": {"type": "keyword"}
                    }
                }
            },
            self.recommendations_index: {
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "recommendation": {"type": "text"},
                        "category": {"type": "keyword"},
                        "priority": {"type": "keyword"}
                    }
                }
            },
            self.health_check_index: {
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "endpoint": {"type": "keyword"},
                        "method": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "status_code": {"type": "integer"},
                        "response_time_ms": {"type": "float"}
                    }
                }
            }
        }
        
        success = True
        for index_name, settings in indices_settings.items():
            try:
                # Check if index exists
                response = self.session.head(f"{self.es_host}/{index_name}")
                
                if response.status_code == 200:
                    self.logger.info(f"Index {index_name} already exists, skipping creation")
                    continue
                
                # Create index with settings
                response = self.session.put(
                    f"{self.es_host}/{index_name}",
                    json=settings
                )
                
                if response.status_code in (200, 201):
                    self.logger.info(f"Created index {index_name}")
                else:
                    self.logger.error(f"Failed to create index {index_name}: {response.text}")
                    success = False
            except Exception as e:
                self.logger.error(f"Error creating index {index_name}: {str(e)}")
                success = False
        
        return success
    
    def index_root_cause_data(self, report: Dict[str, Any]) -> bool:
        """
        Index root cause analysis data into Elasticsearch
        
        Args:
            report: Root cause analysis report
            
        Returns:
            True if successful, False otherwise
        """
        if not report:
            self.logger.error("No root cause report provided")
            return False
        
        self.logger.info("Indexing root cause analysis data")
        
        try:
            # 1. Index error patterns
            if 'error_patterns' in report and 'error_types' in report['error_patterns']:
                self._index_error_patterns(report['error_patterns'])
            
            # 2. Index response time clusters
            if 'response_time_clusters' in report and 'clusters' in report['response_time_clusters']:
                self._index_response_time_clusters(report['response_time_clusters'])
            
            # 3. Index insights
            if 'insights' in report:
                self._index_insights(report['insights'])
            
            # 4. Index recommendations
            if 'recommended_actions' in report:
                self._index_recommendations(report['recommended_actions'])
            
            # 5. Index health checks
            if 'health_check' in report and 'endpoint_health' in report['health_check']:
                self._index_health_checks(report['health_check'])
            
            self.logger.info("Root cause data indexing completed")
            return True
        except Exception as e:
            self.logger.error(f"Error indexing root cause data: {str(e)}")
            return False
    
    def _index_error_patterns(self, error_patterns: Dict[str, Any]) -> None:
        """
        Index error patterns data
        
        Args:
            error_patterns: Error patterns data
        """
        bulk_body = []
        timestamp = datetime.now().isoformat()
        
        for error_type, count in error_patterns.get('error_types', {}).items():
            percentage = error_patterns.get('error_percentages', {}).get(error_type, 0)
            
            # Get pattern details if available
            pattern_details = error_patterns.get('pattern_details', {}).get(error_type, [])
            
            # Group by endpoint and method
            endpoint_method_count = {}
            messages = []
            status_codes = set()
            
            for detail in pattern_details:
                key = (detail.get('endpoint', ''), detail.get('method', ''))
                endpoint_method_count[key] = endpoint_method_count.get(key, 0) + 1
                
                if 'message' in detail and detail['message']:
                    messages.append(detail['message'])
                
                if 'status_code' in detail:
                    status_codes.add(detail['status_code'])
            
            # Create documents for each endpoint/method combination
            for (endpoint, method), count in endpoint_method_count.items():
                doc = {
                    "timestamp": timestamp,
                    "error_type": error_type,
                    "endpoint": endpoint,
                    "method": method,
                    "count": count,
                    "percentage": percentage,
                    "messages": messages[:5],  # Limit to 5 messages
                    "status_codes": list(status_codes)
                }
                
                # Add to bulk indexing request
                bulk_body.append(json.dumps({"index": {"_id": str(uuid.uuid4())}}))
                bulk_body.append(json.dumps(doc))
        
        # Perform bulk indexing if we have documents
        if bulk_body:
            self._bulk_index(self.error_patterns_index, bulk_body)
    
    def _index_response_time_clusters(self, response_time_clusters: Dict[str, Any]) -> None:
        """
        Index response time clusters data
        
        Args:
            response_time_clusters: Response time clusters data
        """
        bulk_body = []
        timestamp = datetime.now().isoformat()
        
        for cluster_id, cluster in response_time_clusters.get('clusters', {}).items():
            # Index each slow endpoint in the cluster
            for endpoint_data in cluster.get('slow_endpoints', []):
                doc = {
                    "timestamp": timestamp,
                    "endpoint": endpoint_data.get('endpoint', ''),
                    "method": endpoint_data.get('method', ''),
                    "avg_response_time": endpoint_data.get('mean_response_time', 0),
                    "max_response_time": cluster.get('max_response_time', 0),
                    "min_response_time": cluster.get('min_response_time', 0),
                    "count": endpoint_data.get('count', 0),
                    "cluster_id": cluster_id
                }
                
                # Add to bulk indexing request
                bulk_body.append(json.dumps({"index": {"_id": str(uuid.uuid4())}}))
                bulk_body.append(json.dumps(doc))
        
        # Perform bulk indexing if we have documents
        if bulk_body:
            self._bulk_index(self.response_time_index, bulk_body)
    
    def _index_insights(self, insights: List[str]) -> None:
        """
        Index insights data
        
        Args:
            insights: List of insights
        """
        bulk_body = []
        timestamp = datetime.now().isoformat()
        
        # Categorize insights
        categories = {
            "error": ["error", "fail", "exception", "invalid"],
            "performance": ["slow", "response time", "latency", "timeout"],
            "traffic": ["traffic", "volume", "request", "spike"],
            "pattern": ["pattern", "correlation", "sequence", "dependency"]
        }
        
        # Severity keywords
        severity_keywords = {
            "high": ["critical", "severe", "significant", "high"],
            "medium": ["elevated", "moderate", "increased"],
            "low": ["minor", "slight", "small"]
        }
        
        for insight in insights:
            # Determine category
            category = "general"
            for cat, keywords in categories.items():
                if any(keyword in insight.lower() for keyword in keywords):
                    category = cat
                    break
            
            # Determine severity
            severity = "medium"
            for sev, keywords in severity_keywords.items():
                if any(keyword in insight.lower() for keyword in keywords):
                    severity = sev
                    break
            
            doc = {
                "timestamp": timestamp,
                "insight": insight,
                "category": category,
                "severity": severity
            }
            
            # Add to bulk indexing request
            bulk_body.append(json.dumps({"index": {"_id": str(uuid.uuid4())}}))
            bulk_body.append(json.dumps(doc))
        
        # Perform bulk indexing if we have documents
        if bulk_body:
            self._bulk_index(self.insights_index, bulk_body)
    
    def _index_recommendations(self, recommendations: List[str]) -> None:
        """
        Index recommendations data
        
        Args:
            recommendations: List of recommendations
        """
        bulk_body = []
        timestamp = datetime.now().isoformat()
        
        # Categorize recommendations
        categories = {
            "authentication": ["auth", "token", "credential", "login"],
            "validation": ["validate", "input", "parameter", "format"],
            "performance": ["performance", "response time", "latency", "timeout", "bottleneck"],
            "monitoring": ["monitor", "alert", "logging", "trace"],
            "architecture": ["circuit breaker", "fallback", "retry", "queue"]
        }
        
        # Priority keywords
        priority_keywords = {
            "high": ["implement", "fix", "critical", "immediately"],
            "medium": ["consider", "review", "improve"],
            "low": ["may", "might", "could", "optional"]
        }
        
        for recommendation in recommendations:
            # Determine category
            category = "general"
            for cat, keywords in categories.items():
                if any(keyword in recommendation.lower() for keyword in keywords):
                    category = cat
                    break
            
            # Determine priority
            priority = "medium"
            for pri, keywords in priority_keywords.items():
                if any(keyword in recommendation.lower() for keyword in keywords):
                    priority = pri
                    break
            
            doc = {
                "timestamp": timestamp,
                "recommendation": recommendation,
                "category": category,
                "priority": priority
            }
            
            # Add to bulk indexing request
            bulk_body.append(json.dumps({"index": {"_id": str(uuid.uuid4())}}))
            bulk_body.append(json.dumps(doc))
        
        # Perform bulk indexing if we have documents
        if bulk_body:
            self._bulk_index(self.recommendations_index, bulk_body)
    
    def _index_health_checks(self, health_check: Dict[str, Any]) -> None:
        """
        Index health check data
        
        Args:
            health_check: Health check data
        """
        bulk_body = []
        timestamp = datetime.now().isoformat()
        
        for endpoint in health_check.get('endpoint_health', []):
            doc = {
                "timestamp": timestamp,
                "endpoint": endpoint.get('endpoint', ''),
                "method": endpoint.get('method', ''),
                "status": endpoint.get('status', 'unknown'),
                "status_code": endpoint.get('status_code', 0),
                "response_time_ms": endpoint.get('response_time_ms', 0)
            }
            
            # Add to bulk indexing request
            bulk_body.append(json.dumps({"index": {"_id": str(uuid.uuid4())}}))
            bulk_body.append(json.dumps(doc))
        
        # Perform bulk indexing if we have documents
        if bulk_body:
            self._bulk_index(self.health_check_index, bulk_body)
    
    def _bulk_index(self, index: str, bulk_body: List[str]) -> None:
        """
        Perform bulk indexing
        
        Args:
            index: Index name
            bulk_body: Bulk indexing request body
        """
        try:
            response = self.session.post(
                f"{self.es_host}/{index}/_bulk",
                data="\n".join(bulk_body) + "\n",
                headers={"Content-Type": "application/x-ndjson"}
            )
            
            if response.status_code >= 200 and response.status_code < 300:
                self.logger.info(f"Bulk indexed {len(bulk_body) // 2} documents to {index}")
            else:
                self.logger.error(f"Failed to bulk index to {index}: {response.text}")
        except Exception as e:
            self.logger.error(f"Error during bulk indexing to {index}: {str(e)}")
    
    def generate_kibana_dashboard_export(self, output_file: str = 'kibana_dashboard.ndjson') -> bool:
        """
        Generate a Kibana dashboard export file that can be imported into Kibana
        
        Args:
            output_file: Path to the output file
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Generating Kibana dashboard export file: {output_file}")
        
        # Create a list of saved objects for the export
        saved_objects = []
        
        # Add index patterns
        index_patterns = [
            self.error_patterns_index,
            self.response_time_index,
            self.insights_index,
            self.recommendations_index,
            self.health_check_index
        ]
        
        for index_pattern in index_patterns:
            saved_objects.append({
                "id": index_pattern,
                "type": "index-pattern",
                "attributes": {
                    "title": f"{index_pattern}*",
                    "timeFieldName": "timestamp"
                },
                "references": []
            })
        
        # Add visualizations
        visualizations = {
            "error_types_pie": {
                "title": "Error Type Distribution",
                "type": "lens",
                "index_pattern": self.error_patterns_index,
                "expression": """
                {
                    "type": "lens",
                    "visualizationType": "pie",
                    "layers": [
                        {
                            "layerId": "layer1",
                            "layerType": "data",
                            "seriesType": "pie",
                            "columns": [
                                {
                                    "columnId": "error_type",
                                    "field": "error_type",
                                    "isBucketed": true,
                                    "operationType": "terms"
                                },
                                {
                                    "columnId": "count",
                                    "field": "count",
                                    "isBucketed": false,
                                    "operationType": "count"
                                }
                            ]
                        }
                    ]
                }
                """
            },
            "response_time_bar": {
                "title": "Endpoint Response Times",
                "type": "lens",
                "index_pattern": self.response_time_index,
                "expression": """
                {
                    "type": "lens",
                    "visualizationType": "bar_stacked",
                    "layers": [
                        {
                            "layerId": "layer1",
                            "layerType": "data",
                            "seriesType": "bar_stacked",
                            "columns": [
                                {
                                    "columnId": "endpoint",
                                    "field": "endpoint",
                                    "isBucketed": true,
                                    "operationType": "terms"
                                },
                                {
                                    "columnId": "method",
                                    "field": "method",
                                    "isBucketed": true,
                                    "operationType": "terms"
                                },
                                {
                                    "columnId": "avg_response_time",
                                    "field": "avg_response_time",
                                    "isBucketed": false,
                                    "operationType": "avg"
                                }
                            ]
                        }
                    ]
                }
                """
            },
            "health_check_status": {
                "title": "Endpoint Health Status",
                "type": "lens",
                "index_pattern": self.health_check_index,
                "expression": """
                {
                    "type": "lens",
                    "visualizationType": "datatable",
                    "layers": [
                        {
                            "layerId": "layer1",
                            "layerType": "data",
                            "columns": [
                                {
                                    "columnId": "endpoint",
                                    "field": "endpoint",
                                    "isBucketed": true,
                                    "operationType": "terms"
                                },
                                {
                                    "columnId": "method",
                                    "field": "method",
                                    "isBucketed": true,
                                    "operationType": "terms"
                                },
                                {
                                    "columnId": "status",
                                    "field": "status",
                                    "isBucketed": true,
                                    "operationType": "terms"
                                },
                                {
                                    "columnId": "response_time_ms",
                                    "field": "response_time_ms",
                                    "isBucketed": false,
                                    "operationType": "avg"
                                }
                            ]
                        }
                    ]
                }
                """
            },
            "insights_tag_cloud": {
                "title": "Insight Keywords",
                "type": "tagcloud",
                "index_pattern": self.insights_index,
                "expression": """
                {
                    "type": "tagcloud",
                    "metric": {
                        "type": "count"
                    },
                    "bucket": {
                        "type": "terms",
                        "field": "insight",
                        "size": 50
                    }
                }
                """
            },
            "recommendations_table": {
                "title": "Recommended Actions",
                "type": "lens",
                "index_pattern": self.recommendations_index,
                "expression": """
                {
                    "type": "lens",
                    "visualizationType": "datatable",
                    "layers": [
                        {
                            "layerId": "layer1",
                            "layerType": "data",
                            "columns": [
                                {
                                    "columnId": "recommendation",
                                    "field": "recommendation",
                                    "isBucketed": true,
                                    "operationType": "terms"
                                },
                                {
                                    "columnId": "category",
                                    "field": "category",
                                    "isBucketed": true,
                                    "operationType": "terms"
                                },
                                {
                                    "columnId": "priority",
                                    "field": "priority",
                                    "isBucketed": true,
                                    "operationType": "terms"
                                }
                            ]
                        }
                    ]
                }
                """
            }
        }
        
        # Add visualization saved objects
        viz_references = []
        for viz_id, viz_data in visualizations.items():
            viz_reference = {
                "id": viz_id,
                "name": viz_data["title"],
                "type": viz_data["type"]
            }
            viz_references.append(viz_reference)
            
            saved_objects.append({
                "id": viz_id,
                "type": viz_data["type"],
                "attributes": {
                    "title": viz_data["title"],
                    "visState": viz_data["expression"],
                    "kibanaSavedObjectMeta": {
                        "searchSourceJSON": json.dumps({
                            "index": viz_data["index_pattern"],
                            "filter": [],
                            "query": { "query": "", "language": "kuery" }
                        })
                    }
                },
                "references": [
                    {
                        "id": viz_data["index_pattern"],
                        "name": "indexpattern-datasource-current-indexpattern",
                        "type": "index-pattern"
                    }
                ]
            })
        
        # Create dashboard saved object
        dashboard_panels = []
        panel_width = 24  # Kibana uses a 48-unit grid system
        panel_height = 6
        y_position = 0
        
        # Add a markdown panel for dashboard description
        dashboard_panels.append({
            "panelIndex": "intro",
            "gridData": {
                "x": 0,
                "y": y_position,
                "w": 48,
                "h": 3,
                "i": "intro"
            },
            "type": "markdown",
            "id": "dashboard-intro",
            "embeddableConfig": {
                "title": "API Root Cause Analysis Dashboard",
                "markdown": """
                # API Root Cause Analysis Dashboard
                This dashboard displays the results of automated root cause analysis for API failures.
                It helps identify patterns, performance issues, and provides recommendations for fixing problems.
                
                **Last updated:** ${timestamp}
                """
            }
        })
        y_position += 3
        
        # Add visualization panels
        for i, (viz_id, viz_data) in enumerate(visualizations.items()):
            # Calculate position (2 visualizations per row)
            x_position = 0 if i % 2 == 0 else panel_width
            if i % 2 == 0 and i > 0:
                y_position += panel_height
            
            dashboard_panels.append({
                "panelIndex": viz_id,
                "gridData": {
                    "x": x_position,
                    "y": y_position,
                    "w": panel_width,
                    "h": panel_height,
                    "i": viz_id
                },
                "type": viz_data["type"],
                "id": viz_id,
                "embeddableConfig": {
                    "title": viz_data["title"]
                }
            })
        
        # Add the dashboard saved object
        saved_objects.append({
            "id": "api-root-cause-dashboard",
            "type": "dashboard",
            "attributes": {
                "title": self.dashboard_name,
                "hits": 0,
                "description": "Dashboard for API Root Cause Analysis",
                "panelsJSON": json.dumps(dashboard_panels),
                "optionsJSON": json.dumps({
                    "useMargins": True,
                    "hidePanelTitles": False
                }),
                "timeRestore": True,
                "timeTo": "now",
                "timeFrom": "now-24h",
                "refreshInterval": {
                    "pause": False,
                    "value": 60000  # Refresh every minute
                }
            },
            "references": viz_references
        })
        
        # Write the saved objects to the export file
        try:
            with open(output_file, 'w') as f:
                for obj in saved_objects:
                    f.write(json.dumps(obj) + '\n')
            
            self.logger.info(f"Kibana dashboard export file created: {output_file}")
            self.logger.info("To import this dashboard, go to Kibana > Stack Management > Saved Objects > Import")
            return True
        except Exception as e:
            self.logger.error(f"Error creating Kibana dashboard export file: {str(e)}")
            return False
    
    def import_dashboard_to_kibana(self, export_file: str = 'kibana_dashboard.ndjson') -> bool:
        """
        Import the dashboard export file into Kibana
        
        Args:
            export_file: Path to the export file
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(export_file):
            self.logger.error(f"Dashboard export file not found: {export_file}")
            return False
        
        self.logger.info(f"Importing dashboard from file: {export_file}")
        
        kibana_url = self.es_host.replace('9200', '5601')
        if not kibana_url.endswith('/'):
            kibana_url += '/'
        
        try:
            with open(export_file, 'rb') as f:
                files = {'file': (export_file, f, 'application/ndjson')}
                
                response = self.session.post(
                    f"{kibana_url}api/saved_objects/_import",
                    files=files,
                    params={
                        'overwrite': 'true'
                    }
                )
                
                if response.status_code in (200, 201):
                    self.logger.info("Dashboard imported successfully")
                    self.logger.info(f"Access your dashboard at: {kibana_url}app/dashboards#/view/api-root-cause-dashboard")
                    return True
                else:
                    self.logger.error(f"Failed to import dashboard: {response.text}")
                    return False
        except Exception as e:
            self.logger.error(f"Error importing dashboard: {str(e)}")
            return False
    
    def configure_kibana_index_patterns(self) -> bool:
        """
        Configure Kibana index patterns for root cause analysis data
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Configuring Kibana index patterns")
        
        kibana_url = self.es_host.replace('9200', '5601')
        if not kibana_url.endswith('/'):
            kibana_url += '/'
        
        # Index patterns to configure
        index_patterns = [
            {
                "id": self.error_patterns_index,
                "title": f"{self.error_patterns_index}*",
                "time_field": "timestamp",
                "fields": [
                    {"name": "timestamp", "type": "date"},
                    {"name": "error_type", "type": "keyword"},
                    {"name": "endpoint", "type": "keyword"},
                    {"name": "method", "type": "keyword"},
                    {"name": "count", "type": "integer"},
                    {"name": "percentage", "type": "float"}
                ]
            },
            {
                "id": self.response_time_index,
                "title": f"{self.response_time_index}*",
                "time_field": "timestamp",
                "fields": [
                    {"name": "timestamp", "type": "date"},
                    {"name": "endpoint", "type": "keyword"},
                    {"name": "method", "type": "keyword"},
                    {"name": "avg_response_time", "type": "float"},
                    {"name": "max_response_time", "type": "float"},
                    {"name": "min_response_time", "type": "float"}
                ]
            },
            {
                "id": self.insights_index,
                "title": f"{self.insights_index}*",
                "time_field": "timestamp",
                "fields": [
                    {"name": "timestamp", "type": "date"},
                    {"name": "insight", "type": "text"},
                    {"name": "category", "type": "keyword"},
                    {"name": "severity", "type": "keyword"}
                ]
            },
            {
                "id": self.recommendations_index,
                "title": f"{self.recommendations_index}*",
                "time_field": "timestamp",
                "fields": [
                    {"name": "timestamp", "type": "date"},
                    {"name": "recommendation", "type": "text"},
                    {"name": "category", "type": "keyword"},
                    {"name": "priority", "type": "keyword"}
                ]
            },
            {
                "id": self.health_check_index,
                "title": f"{self.health_check_index}*",
                "time_field": "timestamp",
                "fields": [
                    {"name": "timestamp", "type": "date"},
                    {"name": "endpoint", "type": "keyword"},
                    {"name": "method", "type": "keyword"},
                    {"name": "status", "type": "keyword"},
                    {"name": "status_code", "type": "integer"},
                    {"name": "response_time_ms", "type": "float"}
                ]
            }
        ]
        
        success = True
        for pattern in index_patterns:
            try:
                # Create index pattern
                response = self.session.post(
                    f"{kibana_url}api/index_patterns/index_pattern",
                    json={
                        "index_pattern": {
                            "title": pattern["title"],
                            "timeFieldName": pattern["time_field"]
                        }
                    }
                )
                
                if response.status_code in (200, 201):
                    self.logger.info(f"Created index pattern: {pattern['title']}")
                else:
                    self.logger.error(f"Failed to create index pattern {pattern['title']}: {response.text}")
                    success = False
            except Exception as e:
                self.logger.error(f"Error creating index pattern {pattern['title']}: {str(e)}")
                success = False
        
        return success
    
    def create_elasticsearch_data_views(self) -> bool:
        """
        Create Elasticsearch data views for Kibana
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Creating Elasticsearch data views")
        
        # Data views to create
        data_views = [
            {
                "name": "API Error Patterns",
                "indices": [self.error_patterns_index],
                "time_field": "timestamp"
            },
            {
                "name": "API Response Times",
                "indices": [self.response_time_index],
                "time_field": "timestamp"
            },
            {
                "name": "API Insights",
                "indices": [self.insights_index],
                "time_field": "timestamp"
            },
            {
                "name": "API Recommendations",
                "indices": [self.recommendations_index],
                "time_field": "timestamp"
            },
            {
                "name": "API Health Checks",
                "indices": [self.health_check_index],
                "time_field": "timestamp"
            },
            {
                "name": "API Root Cause Analysis",
                "indices": [
                    self.error_patterns_index,
                    self.response_time_index,
                    self.insights_index,
                    self.recommendations_index,
                    self.health_check_index
                ],
                "time_field": "timestamp"
            }
        ]
        
        # In a real implementation, you would create these data views
        # using the Kibana API. This is a simplified version.
        for data_view in data_views:
            self.logger.info(f"Would create data view: {data_view['name']} for indices {data_view['indices']}")
        
        return True

def index_root_cause_report(report_path, es_config=None):
    """
    Index a root cause analysis report into Elasticsearch for Kibana visualization
    
    Args:
        report_path: Path to the root cause analysis report JSON file
        es_config: Elasticsearch configuration dictionary (optional)
    
    Returns:
        True if successful, False otherwise
    """
    # Load report
    try:
        with open(report_path, 'r') as f:
            report = json.load(f)
    except Exception as e:
        print(f"Error loading report: {str(e)}")
        return False
    
    # Initialize Kibana integration
    if es_config:
        integration = KibanaRootCauseIntegration(
            es_host=es_config.get('host', 'http://localhost:9200'),
            es_username=es_config.get('username', 'elastic'),
            es_password=es_config.get('password'),
            index_prefix=es_config.get('index_prefix', 'api-monitoring')
        )
    else:
        integration = KibanaRootCauseIntegration()
    
    # Create indices
    if not integration.create_indices():
        print("Failed to create Elasticsearch indices")
        return False
    
    # Index report data
    if not integration.index_root_cause_data(report):
        print("Failed to index root cause data")
        return False
    
    # Generate dashboard export file
    if not integration.generate_kibana_dashboard_export():
        print("Failed to generate Kibana dashboard export file")
        return False
    
    # Try to import dashboard to Kibana
    integration.import_dashboard_to_kibana()
    
    print(f"Root cause report from {report_path} indexed successfully")
    print("You can now view the data in Kibana")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Index root cause analysis data to Elasticsearch/Kibana')
    parser.add_argument('--report', type=str, required=True, help='Path to root cause analysis report JSON file')
    parser.add_argument('--es-host', type=str, default='http://localhost:9200', help='Elasticsearch host URL')
    parser.add_argument('--es-username', type=str, default='elastic', help='Elasticsearch username')
    parser.add_argument('--es-password', type=str, help='Elasticsearch password')
    parser.add_argument('--index-prefix', type=str, default='api-monitoring', help='Index prefix')
    
    args = parser.parse_args()
    
    es_config = {
        'host': args.es_host,
        'username': args.es_username,
        'password': args.es_password,
        'index_prefix': args.index_prefix
    }
    
    index_root_cause_report(args.report, es_config)