import json
import requests
from datetime import datetime
import uuid

class AnomalyReportToKibana:
    def __init__(self, 
                 es_host='http://localhost:9200', 
                 username='elastic', 
                 password=None,
                 index_name='anomaly-reports'):
        """
        Initialize Elasticsearch connection for anomaly report indexing
        
        Args:
            es_host (str): Elasticsearch host URL
            username (str): Elasticsearch username
            password (str): Elasticsearch password
            index_name (str): Name of the index to store anomaly reports
        """
        self.es_host = es_host
        self.username = username
        self.password = password or self._read_es_password()
        self.index_name = index_name
        
        # Create Elasticsearch session
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)

    def _read_es_password(self):
        """
        Read Elasticsearch password from environment or common locations
        
        Returns:
            str: Elasticsearch password
        """
        # Try reading from .env file in the project directory
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('ES_LOCAL_PASSWORD='):
                        return line.split('=')[1].strip().strip('"\'')
        except FileNotFoundError:
            pass
        
        # Fallback prompt
        return input("Enter Elasticsearch password: ")

    def create_index(self):
        """
        Create Elasticsearch index for anomaly reports
        """
        index_settings = {
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date"},
                    "type": {"type": "keyword"},
                    "endpoint": {"type": "keyword"},
                    "method": {"type": "keyword"},
                    "response_time": {"type": "float"},
                    "error_rate": {"type": "float"},
                    "request_count": {"type": "integer"},
                    "z_score": {"type": "float"}
                }
            }
        }
        
        try:
            response = self.session.put(
                f"{self.es_host}/{self.index_name}", 
                json=index_settings
            )
            response.raise_for_status()
            print(f"Index {self.index_name} created successfully")
        except requests.exceptions.RequestException as e:
            print(f"Error creating index: {e}")
            # If index already exists, it's okay to continue
            if response.status_code != 400:
                raise

    def index_anomaly_report(self, report_path='anomaly_report.json'):
        """
        Index anomaly report documents into Elasticsearch
        
        Args:
            report_path (str): Path to the anomaly report JSON file
        """
        try:
            # Read anomaly report
            with open(report_path, 'r') as f:
                report = json.load(f)
        except FileNotFoundError:
            print(f"Anomaly report not found at {report_path}")
            return
        except json.JSONDecodeError:
            print(f"Invalid JSON in {report_path}")
            return

        # Prepare bulk indexing request
        bulk_body = []

        # Process response time anomalies
        for anomaly in report.get('response_time_anomalies', []):
            doc = {
                "type": "response_time_anomaly",
                "timestamp": anomaly.get('timestamp'),
                "endpoint": anomaly.get('endpoint'),
                "method": anomaly.get('method'),
                "response_time": anomaly.get('response_time'),
                "z_score": anomaly.get('z_score')
            }
            bulk_body.append(json.dumps({"index": {"_id": str(uuid.uuid4())}}))
            bulk_body.append(json.dumps(doc))

        # Process error pattern anomalies
        for anomaly in report.get('error_pattern_anomalies', []):
            doc = {
                "type": "error_pattern_anomaly",
                "endpoint": anomaly.get('endpoint'),
                "method": anomaly.get('method'),
                "total_requests": anomaly.get('total_requests'),
                "error_requests": anomaly.get('error_requests'),
                "error_rate": anomaly.get('error_rate')
            }
            bulk_body.append(json.dumps({"index": {"_id": str(uuid.uuid4())}}))
            bulk_body.append(json.dumps(doc))

        # Process traffic anomalies
        for anomaly in report.get('traffic_anomalies', []):
            doc = {
                "type": "traffic_anomaly",
                "timestamp": anomaly.get('timestamp'),
                "request_count": anomaly.get('request_count'),
                "z_score": anomaly.get('z_score')
            }
            bulk_body.append(json.dumps({"index": {"_id": str(uuid.uuid4())}}))
            bulk_body.append(json.dumps(doc))

        # Bulk index documents
        if bulk_body:
            try:
                response = self.session.post(
                    f"{self.es_host}/{self.index_name}/_bulk",
                    data="\n".join(bulk_body) + "\n",
                    headers={"Content-Type": "application/x-ndjson"}
                )
                response.raise_for_status()
                print("Anomaly report successfully indexed")
            except requests.exceptions.RequestException as e:
                print(f"Error indexing anomaly report: {e}")
        else:
            print("No anomalies to index")

    def generate_kibana_dashboards(self):
        """
        Generate example Kibana dashboard configuration
        
        Note: This is a template. Actual dashboard creation requires 
        manual configuration in Kibana UI.
        """
        dashboard_template = {
            "title": "API Anomaly Dashboard",
            "visualizations": [
                {
                    "title": "Response Time Anomalies",
                    "type": "line",
                    "index_pattern": self.index_name,
                    "query": {
                        "query": 'type:"response_time_anomaly"',
                        "language": "kuery"
                    }
                },
                {
                    "title": "Error Rate Anomalies",
                    "type": "area",
                    "index_pattern": self.index_name,
                    "query": {
                        "query": 'type:"error_pattern_anomaly"',
                        "language": "kuery"
                    }
                },
                {
                    "title": "Traffic Anomalies",
                    "type": "bar",
                    "index_pattern": self.index_name,
                    "query": {
                        "query": 'type:"traffic_anomaly"',
                        "language": "kuery"
                    }
                }
            ]
        }
        
        # Save dashboard template
        with open('kibana_dashboard_template.json', 'w') as f:
            json.dump(dashboard_template, f, indent=2)
        
        print("Kibana dashboard template generated")

def main():
    # Initialize Kibana indexer
    kibana_indexer = AnomalyReportToKibana()
    
    # Create index
    kibana_indexer.create_index()
    
    # Index anomaly report
    kibana_indexer.index_anomaly_report()
    
    # Generate dashboard template
    kibana_indexer.generate_kibana_dashboards()

if __name__ == "__main__":
    main()