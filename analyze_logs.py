import json
import pandas as pd
import numpy as np
from collections import defaultdict
import logging

class APIAnomalyDetector:
    def __init__(self, log_file='/Users/abhaykumar/codeit/projects/Machine_Learning/API_LOG/dock/logs/api_logs.json', 
                 response_time_threshold=1500,  # ms
                 error_rate_threshold=0.3,      # 30% error rate
                 consecutive_error_threshold=3):
        """
        Initialize the Anomaly Detector with configurable thresholds
        
        Args:
            log_file (str): Path to the JSON log file
            response_time_threshold (int): Max acceptable response time in ms
            error_rate_threshold (float): Maximum acceptable error rate
            consecutive_error_threshold (int): Max consecutive errors before flagging
        """
        self.log_file = log_file
        self.response_time_threshold = response_time_threshold
        self.error_rate_threshold = error_rate_threshold
        self.consecutive_error_threshold = consecutive_error_threshold
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s: %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def load_logs(self):
        """
        Load logs from JSON file
        
        Returns:
            pd.DataFrame: Loaded logs
        """
        try:
            with open(self.log_file, 'r') as f:
                logs = [json.loads(line.strip()) for line in f]
            
            if not logs:
                self.logger.warning("Log file is empty.")
                return pd.DataFrame()

            df = pd.DataFrame(logs)
            
            if 'timestamp' not in df.columns:
                self.logger.error(f"'timestamp' column not found in logs. Available columns: {df.columns.tolist()}")
                return pd.DataFrame()

            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

            if df['timestamp'].isnull().any():
                self.logger.warning("Some timestamps could not be parsed.")

            return df

        except FileNotFoundError:
            self.logger.error(f"Log file {self.log_file} not found.")
            return pd.DataFrame()
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {self.log_file}: {str(e)}")
            return pd.DataFrame()


    def detect_response_time_anomalies(self, df):
        """
        Detect anomalies based on response time
        
        Args:
            df (pd.DataFrame): Logs dataframe
        
        Returns:
            list: List of response time anomalies
        """
        # Group by endpoint to calculate baseline
        endpoint_stats = df.groupby('endpoint')['response_time_ms'].agg(['mean', 'std'])
        
        response_anomalies = []
        for _, row in df.iterrows():
            # Check if response time exceeds threshold or z-score
            endpoint_mean = endpoint_stats.loc[row['endpoint'], 'mean']
            endpoint_std = endpoint_stats.loc[row['endpoint'], 'std']
            
            # Z-score check
            z_score = (row['response_time_ms'] - endpoint_mean) / (endpoint_std or 1)
            
            if (row['response_time_ms'] > self.response_time_threshold or 
                abs(z_score) > 3):  # More than 3 standard deviations
                response_anomalies.append({
                    'type': 'Response Time Anomaly',
                    'endpoint': row['endpoint'],
                    'method': row['method'],
                    'timestamp': str(row['timestamp']),
                    'response_time': row['response_time_ms'],
                    'mean_response_time': endpoint_mean,
                    'z_score': z_score
                })
        
        return response_anomalies

    def detect_error_pattern_anomalies(self, df):
        """
        Detect anomalies based on error patterns
        
        Args:
            df (pd.DataFrame): Logs dataframe
        
        Returns:
            list: List of error pattern anomalies
        """
        error_anomalies = []
        
        # Group by endpoint and method
        grouped = df.groupby(['endpoint', 'method'])
        
        for (endpoint, method), group in grouped:
            # Calculate overall error rate
            total_requests = len(group)
            error_requests = len(group[group['status_code'] >= 400])
            error_rate = error_requests / total_requests if total_requests > 0 else 0
            
            # Check for consecutive errors
            consecutive_errors = 0
            max_consecutive_errors = 0
            
            for status in group['status_code']:
                if status >= 400:
                    consecutive_errors += 1
                    max_consecutive_errors = max(max_consecutive_errors, consecutive_errors)
                else:
                    consecutive_errors = 0
            
            # Flag anomalies
            if (error_rate > self.error_rate_threshold or 
                max_consecutive_errors >= self.consecutive_error_threshold):
                error_anomalies.append({
                    'type': 'Error Pattern Anomaly',
                    'endpoint': endpoint,
                    'method': method,
                    'total_requests': total_requests,
                    'error_requests': error_requests,
                    'error_rate': error_rate,
                    'max_consecutive_errors': max_consecutive_errors
                })
        
        return error_anomalies

    def detect_traffic_anomalies(self, df):
        """
        Detect traffic-related anomalies
        
        Args:
            df (pd.DataFrame): Logs dataframe
        
        Returns:
            list: List of traffic anomalies
        """
        traffic_anomalies = []
        
        # Resample by time intervals and count requests
        time_grouped = df.resample('5T', on='timestamp')
        request_counts = time_grouped.size()
        
        # Calculate mean and standard deviation of request counts
        mean_requests = request_counts.mean()
        std_requests = request_counts.std()
        
        # Identify traffic spikes or drops
        for timestamp, count in request_counts.items():
            z_score = (count - mean_requests) / (std_requests or 1)
            
            if abs(z_score) > 3:  # More than 3 standard deviations
                traffic_anomalies.append({
                    'type': 'Traffic Anomaly',
                    'timestamp': str(timestamp),
                    'request_count': count,
                    'mean_requests': mean_requests,
                    'z_score': z_score
                })
        
        return traffic_anomalies

    def generate_report(self, df):
        """
        Generate a comprehensive anomaly report
        
        Args:
            df (pd.DataFrame): Logs dataframe
        
        Returns:
            dict: Comprehensive anomaly report
        """
        # Detect different types of anomalies
        response_anomalies = self.detect_response_time_anomalies(df)
        error_anomalies = self.detect_error_pattern_anomalies(df)
        traffic_anomalies = self.detect_traffic_anomalies(df)
        
        # Compile report
        report = {
            'total_logs': len(df),
            'response_time_anomalies': response_anomalies,
            'error_pattern_anomalies': error_anomalies,
            'traffic_anomalies': traffic_anomalies
        }
        
        return report

    def run(self):
        """
        Main method to run anomaly detection
        """
        # Load logs
        df = self.load_logs()
        
        if df.empty:
            self.logger.warning("No logs to analyze.")
            return None
        
        # Generate anomaly report
        report = self.generate_report(df)
        
        # Log summary
        self.logger.info("Anomaly Detection Summary:")
        self.logger.info(f"Total Logs: {report['total_logs']}")
        self.logger.info(f"Response Time Anomalies: {len(report['response_time_anomalies'])}")
        self.logger.info(f"Error Pattern Anomalies: {len(report['error_pattern_anomalies'])}")
        self.logger.info(f"Traffic Anomalies: {len(report['traffic_anomalies'])}")
        
        return report

def main():
    # Create and run anomaly detector
    detector = APIAnomalyDetector()
    anomaly_report = detector.run()
    
    # Optional: Save report to JSON
    if anomaly_report:
        import json
        with open('anomaly_report.json', 'w') as f:
            json.dump(anomaly_report, f, indent=2)

if __name__ == "__main__":
    main()