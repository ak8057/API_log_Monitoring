import json
import pandas as pd
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta

class ErrorRateMonitor:
    def __init__(self, 
                 log_file: str = '/Users/abhaykumar/codeit/projects/Machine_Learning/API_LOG/dock/logs/api_logs.json', 
                 error_threshold: float = 0.3,
                 consecutive_error_threshold: int = 5):
        """
        Initialize Error Rate Monitor
        
        Args:
            log_file (str): Path to API logs
            error_threshold (float): Threshold for error rate (default 30%)
            consecutive_error_threshold (int): Max consecutive errors before alerting
        """
        self.log_file = log_file
        self.error_threshold = error_threshold
        self.consecutive_error_threshold = consecutive_error_threshold
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s: %(message)s',
            filename='error_rate_monitor.log'
        )
        self.logger = logging.getLogger(__name__)

    def load_logs(self) -> pd.DataFrame:
        """
        Load logs from JSON file
        
        Returns:
            pd.DataFrame: Loaded logs
        """
        try:
            with open(self.log_file, 'r') as f:
                logs = [json.loads(line.strip()) for line in f]
            
            df = pd.DataFrame(logs)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except FileNotFoundError:
            self.logger.error(f"Log file {self.log_file} not found.")
            return pd.DataFrame()
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in {self.log_file}")
            return pd.DataFrame()

    def analyze_error_rates(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze error rates across different dimensions
        
        Args:
            df (pd.DataFrame): Logs dataframe
        
        Returns:
            Dict containing error rate analysis
        """
        if df.empty:
            return {}

        # Analyze error rates by endpoint and method
        error_analysis = {
            'overall_analysis': self._calculate_error_metrics(df),
            'endpoint_analysis': {},
            'method_analysis': {},
            'environment_analysis': {}
        }

        # Endpoint-level analysis
        endpoint_groups = df.groupby('endpoint')
        for endpoint, group in endpoint_groups:
            error_analysis['endpoint_analysis'][endpoint] = self._calculate_error_metrics(group, endpoint)

        # Method-level analysis
        method_groups = df.groupby('method')
        for method, group in method_groups:
            error_analysis['method_analysis'][method] = self._calculate_error_metrics(group, method)

        # Environment-level analysis
        env_groups = df.groupby('environment')
        for env, group in env_groups:
            error_analysis['environment_analysis'][env] = self._calculate_error_metrics(group, env)

        return error_analysis

    def _calculate_error_metrics(self, 
                                  group: pd.DataFrame, 
                                  identifier: str = 'Overall') -> Dict[str, Any]:
        """
        Calculate error metrics for a specific group
        
        Args:
            group (pd.DataFrame): Grouped logs
            identifier (str): Identifier for the group
        
        Returns:
            Dict with error metrics
        """
        total_requests = len(group)
        error_requests = len(group[group['status_code'] >= 400])
        
        # Calculate error rate
        error_rate = error_requests / total_requests if total_requests > 0 else 0
        
        # Consecutive error tracking
        consecutive_errors = self._count_consecutive_errors(group)
        
        # Prepare metrics
        metrics = {
            'total_requests': total_requests,
            'error_requests': error_requests,
            'error_rate': error_rate,
            'max_consecutive_errors': consecutive_errors,
            'is_anomalous': (error_rate > self.error_threshold or 
                             consecutive_errors >= self.consecutive_error_threshold)
        }
        
        # Log anomalies
        if metrics['is_anomalous']:
            self.logger.warning(f"Anomaly detected for {identifier}: {metrics}")
        
        return metrics

    def _count_consecutive_errors(self, group: pd.DataFrame) -> int:
        """
        Count maximum consecutive errors
        
        Args:
            group (pd.DataFrame): Grouped logs
        
        Returns:
            int: Maximum number of consecutive errors
        """
        # Sort by timestamp to ensure correct order
        sorted_group = group.sort_values('timestamp')
        
        # Track consecutive errors
        max_consecutive = 0
        current_consecutive = 0
        
        for status in sorted_group['status_code']:
            if status >= 400:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive

    def generate_error_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive error rate report
        
        Returns:
            Dict containing error analysis
        """
        # Load logs
        df = self.load_logs()
        
        if df.empty:
            self.logger.warning("No logs to analyze.")
            return {}
        
        # Analyze error rates
        error_analysis = self.analyze_error_rates(df)
        
        # Save report to JSON
        report_filename = f'error_rate_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_filename, 'w') as f:
            json.dump(error_analysis, f, indent=2, default=str)
        
        self.logger.info(f"Error rate report generated: {report_filename}")
        
        return error_analysis

def main():
    # Initialize Error Rate Monitor
    monitor = ErrorRateMonitor()
    
    # Generate and print error report
    error_report = monitor.generate_error_report()
    
    # Print summary
    print("\n--- Error Rate Analysis Summary ---")
    
    # Overall Analysis
    overall = error_report.get('overall_analysis', {})
    print(f"Total Requests: {overall.get('total_requests', 0)}")
    print(f"Error Requests: {overall.get('error_requests', 0)}")
    print(f"Overall Error Rate: {overall.get('error_rate', 0):.2%}")
    
    # Highlight Anomalous Endpoints
    print("\nAnomalous Endpoints:")
    for endpoint, metrics in error_report.get('endpoint_analysis', {}).items():
        if metrics.get('is_anomalous'):
            print(f"- {endpoint}: {metrics['error_rate']:.2%} error rate")

if __name__ == "__main__":
    main()