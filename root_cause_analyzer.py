import json
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from collections import defaultdict
import logging
import re
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Any, Tuple, Optional

class APIRootCauseAnalyzer:
    def __init__(self, 
                 log_file='/Users/abhaykumar/codeit/projects/Machine_Learning/API_LOG/dock/logs/api_logs.json',
                 error_threshold=0.2,
                 analysis_window_hours=24):
        """
        Initialize the API Root Cause Analyzer
        
        Args:
            log_file (str): Path to API logs
            error_threshold (float): Threshold for error rate before detailed analysis
            analysis_window_hours (int): Hours of logs to analyze for patterns
        """
        self.log_file = log_file
        self.error_threshold = error_threshold
        self.analysis_window_hours = analysis_window_hours
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s: %(message)s',
            filename='api_root_cause.log'
        )
        self.logger = logging.getLogger(__name__)
        
        # Patterns for common error causes
        self.error_patterns = {
            'auth_failure': ['unauthorized', 'forbidden', 'auth fail', 'not authenticated', 'invalid token', 'token expired'],
            'rate_limit': ['rate limit', 'too many requests', 'request quota', 'throttled'],
            'invalid_input': ['invalid input', 'invalid parameter', 'validation error', 'bad request', 'malformed'],
            'timeout': ['timeout', 'timed out', 'deadline exceeded', 'connection timeout'],
            'resource_unavailable': ['not found', 'no such resource', 'resource unavailable', 'does not exist'],
            'server_error': ['internal server error', 'service unavailable', 'internal error', 'server error'],
            'dependency_failure': ['dependency failed', 'upstream service', 'downstream service', 'service dependency'],
            'concurrency': ['conflict', 'race condition', 'already exists', 'duplicate']
        }

    def load_logs(self) -> pd.DataFrame:
        """
        Load logs from JSON file with error handling
        
        Returns:
            pd.DataFrame: Loaded logs
        """
        try:
            with open(self.log_file, 'r') as f:
                logs = [json.loads(line.strip()) for line in f]
            
            if not logs:
                self.logger.warning("Log file is empty")
                return pd.DataFrame()
                
            df = pd.DataFrame(logs)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter logs for analysis window
            cutoff_time = datetime.now() - timedelta(hours=self.analysis_window_hours)
            df = df[df['timestamp'] > cutoff_time]
            
            return df
        except FileNotFoundError:
            self.logger.error(f"Log file {self.log_file} not found")
            return pd.DataFrame()
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in {self.log_file}")
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error loading logs: {str(e)}")
            return pd.DataFrame()

    def identify_error_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Identify patterns in error responses
        
        Args:
            df (pd.DataFrame): Logs dataframe
        
        Returns:
            Dict with error patterns analysis
        """
        if df.empty:
            return {}
            
        # Filter error responses
        errors_df = df[df['status_code'] >= 400].copy()
        if errors_df.empty:
            return {'error_count': 0, 'error_rate': 0, 'patterns': {}}
            
        total_requests = len(df)
        error_count = len(errors_df)
        error_rate = error_count / total_requests
        
        # Initialize pattern counters
        error_types = defaultdict(int)
        pattern_details = defaultdict(list)
        
        # Analyze error responses for patterns
        for _, row in errors_df.iterrows():
            # Extract error message from response body
            error_message = ''
            if isinstance(row.get('response_body'), dict) and 'error' in row['response_body']:
                error_message = str(row['response_body']['error']).lower()
            
            # Match error message against known patterns
            matched_pattern = False
            for pattern_name, keywords in self.error_patterns.items():
                if any(keyword in error_message for keyword in keywords):
                    error_types[pattern_name] += 1
                    pattern_details[pattern_name].append({
                        'timestamp': row['timestamp'],
                        'endpoint': row['endpoint'],
                        'method': row['method'],
                        'status_code': row['status_code'],
                        'message': error_message
                    })
                    matched_pattern = True
                    break
            
            # If no pattern matched, count as unclassified
            if not matched_pattern:
                error_types['unclassified'] += 1
                pattern_details['unclassified'].append({
                    'timestamp': row['timestamp'],
                    'endpoint': row['endpoint'],
                    'method': row['method'],
                    'status_code': row['status_code'],
                    'message': error_message
                })
        
        # Calculate percentages for each error type
        error_percentages = {k: (v / error_count * 100) for k, v in error_types.items()}
        
        return {
            'error_count': error_count,
            'error_rate': error_rate,
            'error_types': dict(error_types),
            'error_percentages': error_percentages,
            'pattern_details': pattern_details
        }

    def cluster_response_times(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Use clustering to identify groups of similar response times
        that might indicate performance issues
        
        Args:
            df (pd.DataFrame): Logs dataframe
        
        Returns:
            Dict with response time clustering analysis
        """
        if df.empty or 'response_time_ms' not in df.columns:
            return {}
            
        # Prepare data for clustering
        X = df['response_time_ms'].values.reshape(-1, 1)
        
        # Use DBSCAN for clustering
        clustering = DBSCAN(eps=200, min_samples=5).fit(X)
        labels = clustering.labels_
        df_copy = df.copy()
        df_copy['cluster'] = labels
        
        # Analyze clusters
        clusters = {}
        for label in set(labels):
            if label == -1:
                # -1 represents noise points in DBSCAN
                continue
                
            cluster_df = df_copy[df_copy['cluster'] == label]
            
            # Calculate cluster stats
            avg_response_time = cluster_df['response_time_ms'].mean()
            min_response_time = cluster_df['response_time_ms'].min()
            max_response_time = cluster_df['response_time_ms'].max()
            
            # Group by endpoint and method to find potential hotspots
            endpoint_stats = cluster_df.groupby(['endpoint', 'method']).agg({
                'response_time_ms': ['count', 'mean', 'min', 'max']
            }).reset_index()
            
            # Identify slow endpoints in this cluster
            slow_endpoints = []
            for _, row in endpoint_stats.iterrows():
                endpoint = row['endpoint']
                method = row['method']
                count = row[('response_time_ms', 'count')]
                mean = row[('response_time_ms', 'mean')]
                
                slow_endpoints.append({
                    'endpoint': endpoint,
                    'method': method,
                    'count': count,
                    'mean_response_time': mean
                })
            
            clusters[f"cluster_{label}"] = {
                'size': len(cluster_df),
                'avg_response_time': avg_response_time,
                'min_response_time': min_response_time,
                'max_response_time': max_response_time,
                'slow_endpoints': slow_endpoints
            }
        
        return {
            'cluster_count': len(clusters),
            'clusters': clusters
        }

    def analyze_sequence_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze sequences of API calls to identify correlation between calls
        and potential dependency-related failures
        
        Args:
            df (pd.DataFrame): Logs dataframe
        
        Returns:
            Dict with sequence pattern analysis
        """
        if df.empty:
            return {}
            
        # Sort by timestamp
        df_sorted = df.sort_values('timestamp')
        
        # Group by client IP to separate different sessions
        sequences = {}
        for client_ip, group in df_sorted.groupby('client_ip'):
            # For each client IP, analyze the sequence of API calls
            call_sequence = []
            error_sequences = []
            current_error_sequence = []
            
            for _, row in group.iterrows():
                endpoint = row['endpoint']
                method = row['method']
                status_code = row['status_code']
                call = f"{method} {endpoint}"
                
                call_sequence.append({
                    'call': call,
                    'timestamp': row['timestamp'],
                    'status_code': status_code,
                    'response_time': row.get('response_time_ms')
                })
                
                # Track sequences leading to errors
                if status_code >= 400:
                    current_error_sequence.append(call)
                    # If we have a sequence of 3 or more calls leading to an error, save it
                    if len(call_sequence) >= 3:
                        error_context = call_sequence[-3:]
                        error_sequences.append({
                            'error_endpoint': call,
                            'status_code': status_code,
                            'preceding_calls': [item['call'] for item in error_context[:-1]],
                            'timestamp': row['timestamp']
                        })
                else:
                    current_error_sequence = []
            
            sequences[client_ip] = {
                'call_count': len(call_sequence),
                'error_sequences': error_sequences
            }
        
        # Analyze common patterns in error sequences
        common_patterns = defaultdict(int)
        all_error_sequences = []
        
        for client_data in sequences.values():
            for seq in client_data['error_sequences']:
                # Create a pattern string from the sequence
                pattern = ' -> '.join(seq['preceding_calls']) + ' -> ' + seq['error_endpoint']
                common_patterns[pattern] += 1
                all_error_sequences.append(seq)
        
        # Sort patterns by frequency
        sorted_patterns = sorted(common_patterns.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'client_count': len(sequences),
            'common_error_patterns': dict(sorted_patterns),
            'error_sequences': all_error_sequences
        }

    def analyze_periodic_failures(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze time-based patterns in failures
        
        Args:
            df (pd.DataFrame): Logs dataframe
        
        Returns:
            Dict with time-based failure analysis
        """
        if df.empty:
            return {}
        
        # Filter error responses
        errors_df = df[df['status_code'] >= 400].copy()
        if errors_df.empty:
            return {}
            
        # Group errors by hour
        errors_df['hour'] = errors_df['timestamp'].dt.hour
        hourly_errors = errors_df.groupby('hour').size()
        
        # Group all requests by hour for comparison
        all_df = df.copy()
        all_df['hour'] = all_df['timestamp'].dt.hour
        hourly_requests = all_df.groupby('hour').size()
        
        # Calculate hourly error rates
        hourly_error_rates = {}
        for hour in range(24):
            if hour in hourly_requests:
                error_count = hourly_errors.get(hour, 0)
                request_count = hourly_requests[hour]
                error_rate = error_count / request_count if request_count > 0 else 0
                hourly_error_rates[hour] = {
                    'error_count': int(error_count),
                    'request_count': int(request_count),
                    'error_rate': error_rate
                }
            else:
                hourly_error_rates[hour] = {
                    'error_count': 0,
                    'request_count': 0,
                    'error_rate': 0
                }
                
        # Find hours with elevated error rates
        avg_error_rate = errors_df.shape[0] / df.shape[0]
        problematic_hours = {}
        
        for hour, data in hourly_error_rates.items():
            if data['request_count'] > 0 and data['error_rate'] > (avg_error_rate * 1.5):
                problematic_hours[hour] = data
        
        return {
            'hourly_error_rates': hourly_error_rates,
            'problematic_hours': problematic_hours,
            'avg_error_rate': avg_error_rate
        }

    def analyze_dependency_correlation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze if there are correlations between failures across different endpoints
        that might indicate dependency relationships
        
        Args:
            df (pd.DataFrame): Logs dataframe
        
        Returns:
            Dict with dependency correlation analysis
        """
        if df.empty:
            return {}
            
        # Analyze failures by timestamp
        df_with_minute = df.copy()
        # Round timestamps to the nearest minute to group related calls
        df_with_minute['minute'] = df_with_minute['timestamp'].dt.floor('T')
        
        # Find minutes with errors
        error_minutes = set(df_with_minute[df_with_minute['status_code'] >= 400]['minute'])
        
        # For each error minute, check which endpoints had errors
        endpoint_correlations = defaultdict(lambda: defaultdict(int))
        
        for minute in error_minutes:
            minute_df = df_with_minute[df_with_minute['minute'] == minute]
            error_endpoints = set(minute_df[minute_df['status_code'] >= 400]['endpoint'])
            
            # Record co-occurrence of errors
            for endpoint1 in error_endpoints:
                for endpoint2 in error_endpoints:
                    if endpoint1 != endpoint2:
                        endpoint_correlations[endpoint1][endpoint2] += 1
        
        # Find likely dependencies
        likely_dependencies = []
        for endpoint, correlations in endpoint_correlations.items():
            for correlated_endpoint, count in correlations.items():
                if count >= 3:  # Threshold for considering it a pattern
                    likely_dependencies.append({
                        'source_endpoint': endpoint,
                        'dependent_endpoint': correlated_endpoint,
                        'co_failure_count': count
                    })
        
        return {
            'endpoint_correlations': {k: dict(v) for k, v in endpoint_correlations.items()},
            'likely_dependencies': likely_dependencies
        }

    def generate_failure_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive failure analysis report
        
        Returns:
            Dict containing detailed failure analysis
        """
        # Load logs
        df = self.load_logs()
        
        if df.empty:
            self.logger.warning("No logs to analyze")
            return {'status': 'error', 'message': 'No logs available for analysis'}
        
        # Compute overall error rate
        total_requests = len(df)
        error_requests = len(df[df['status_code'] >= 400])
        error_rate = error_requests / total_requests if total_requests > 0 else 0
        
        # Skip detailed analysis if error rate is below threshold
        if error_rate < self.error_threshold and error_requests < 10:
            return {
                'status': 'success',
                'total_requests': total_requests,
                'error_requests': error_requests,
                'error_rate': error_rate,
                'message': 'Error rate below threshold, no detailed analysis performed'
            }
        
        # Perform detailed analysis
        error_patterns = self.identify_error_patterns(df)
        response_time_clusters = self.cluster_response_times(df)
        sequence_patterns = self.analyze_sequence_patterns(df)
        periodic_failures = self.analyze_periodic_failures(df)
        dependency_correlations = self.analyze_dependency_correlation(df)
        
        # Generate overall insights
        insights = self._generate_insights(
            error_patterns, 
            response_time_clusters,
            sequence_patterns,
            periodic_failures,
            dependency_correlations
        )
        
        # Prepare recommended actions
        recommended_actions = self._generate_recommendations(
            error_patterns,
            response_time_clusters,
            sequence_patterns,
            periodic_failures,
            dependency_correlations
        )
        
        # Save report to JSON
        report_filename = f'api_failure_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        report = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'total_requests': total_requests,
            'error_requests': error_requests,
            'error_rate': error_rate,
            'error_patterns': error_patterns,
            'response_time_clusters': response_time_clusters,
            'sequence_patterns': sequence_patterns,
            'periodic_failures': periodic_failures,
            'dependency_correlations': dependency_correlations,
            'insights': insights,
            'recommended_actions': recommended_actions
        }
        
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Failure analysis report generated: {report_filename}")
        
        return report

    def _generate_insights(self, 
                          error_patterns: Dict, 
                          response_time_clusters: Dict,
                          sequence_patterns: Dict,
                          periodic_failures: Dict,
                          dependency_correlations: Dict) -> List[str]:
        """
        Generate human-readable insights from the analysis
        
        Args:
            Various analysis results
        
        Returns:
            List of insight strings
        """
        insights = []
        
        # Error pattern insights
        if error_patterns and 'error_types' in error_patterns:
            error_types = error_patterns['error_types']
            total_errors = sum(error_types.values())
            
            # Add insights for the most common error types
            if total_errors > 0:
                for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:3]:
                    percentage = (count / total_errors) * 100
                    if percentage >= 20:  # Only report significant patterns
                        insights.append(f"{error_type.replace('_', ' ').title()} errors account for {percentage:.1f}% of all failures")
        
        # Response time insights
        if response_time_clusters and 'clusters' in response_time_clusters:
            clusters = response_time_clusters['clusters']
            for cluster_name, cluster_data in clusters.items():
                # Report on large, slow clusters
                if cluster_data['size'] >= 10 and cluster_data['avg_response_time'] > 1000:
                    insights.append(f"Identified a group of {cluster_data['size']} requests with consistently high response times (avg: {cluster_data['avg_response_time']:.1f}ms)")
                    
                    # Report on the slowest endpoints in this cluster
                    if 'slow_endpoints' in cluster_data and cluster_data['slow_endpoints']:
                        slowest = sorted(cluster_data['slow_endpoints'], key=lambda x: x['mean_response_time'], reverse=True)[0]
                        insights.append(f"The slowest endpoint in this group is {slowest['method']} {slowest['endpoint']} with average response time of {slowest['mean_response_time']:.1f}ms")
        
        # Sequence pattern insights
        if sequence_patterns and 'common_error_patterns' in sequence_patterns:
            common_patterns = sequence_patterns['common_error_patterns']
            # Report on the most common error sequences
            for pattern, count in list(common_patterns.items())[:2]:
                if count >= 3:  # Only report patterns with significant occurrence
                    insights.append(f"Detected a common error pattern ({count} occurrences): {pattern}")
        
        # Periodic failure insights
        if periodic_failures and 'problematic_hours' in periodic_failures:
            problematic_hours = periodic_failures['problematic_hours']
            if problematic_hours:
                hours_list = sorted(problematic_hours.keys())
                if len(hours_list) == 1:
                    hour = hours_list[0]
                    insights.append(f"Hour {hour}:00 shows elevated error rates ({problematic_hours[hour]['error_rate']:.1%}), which may indicate scheduled jobs or maintenance windows")
                elif len(hours_list) > 1:
                    hours_str = ', '.join([f"{h}:00" for h in hours_list])
                    insights.append(f"Multiple hours show elevated error rates: {hours_str}")
        
        # Dependency correlation insights
        if dependency_correlations and 'likely_dependencies' in dependency_correlations:
            dependencies = dependency_correlations['likely_dependencies']
            if dependencies:
                # Report on the strongest dependency correlations
                strongest = sorted(dependencies, key=lambda x: x['co_failure_count'], reverse=True)
                if strongest:
                    dep = strongest[0]
                    insights.append(f"Detected potential dependency: failures on {dep['source_endpoint']} correlate with failures on {dep['dependent_endpoint']} ({dep['co_failure_count']} co-occurrences)")
        
        return insights

    def _generate_recommendations(self, 
                                 error_patterns: Dict, 
                                 response_time_clusters: Dict,
                                 sequence_patterns: Dict,
                                 periodic_failures: Dict,
                                 dependency_correlations: Dict) -> List[str]:
        """
        Generate recommendations based on the analysis
        
        Args:
            Various analysis results
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Error pattern recommendations
        if error_patterns and 'error_types' in error_patterns:
            error_types = error_patterns['error_types']
            
            # Specific recommendations based on error types
            if 'auth_failure' in error_types and error_types['auth_failure'] > 0:
                recommendations.append("Review authentication mechanisms and token lifetimes to address authentication failures")
                
            if 'rate_limit' in error_types and error_types['rate_limit'] > 0:
                recommendations.append("Implement client-side rate limiting or request queuing to prevent rate limit errors")
                
            if 'invalid_input' in error_types and error_types['invalid_input'] > 0:
                recommendations.append("Enhance input validation on the client side before sending requests")
                
            if 'timeout' in error_types and error_types['timeout'] > 0:
                recommendations.append("Implement retry mechanisms with exponential backoff for requests that time out")
                
            if 'server_error' in error_types and error_types['server_error'] > 0:
                recommendations.append("Check server logs for exceptions and consider implementing circuit breakers for unstable services")
                
            if 'unclassified' in error_types and error_types['unclassified'] > 5:
                recommendations.append("Implement more detailed error messages in API responses to better classify unidentified errors")
        
        # Response time recommendations
        if response_time_clusters and 'clusters' in response_time_clusters:
            clusters = response_time_clusters['clusters']
            has_slow_cluster = False
            
            for _, cluster_data in clusters.items():
                if cluster_data['avg_response_time'] > 1500:  # Very slow requests
                    has_slow_cluster = True
                    break
                    
            if has_slow_cluster:
                recommendations.append("Consider implementing performance tracing to identify bottlenecks in slow endpoints")
                recommendations.append("Review database queries and external service calls in the slowest endpoints")
        
        # Sequence pattern recommendations
        if sequence_patterns and 'common_error_patterns' in sequence_patterns:
            if sequence_patterns['common_error_patterns']:
                recommendations.append("Analyze API call sequences to identify and fix dependency chains that lead to failures")
        
        # Periodic failure recommendations
        if periodic_failures and 'problematic_hours' in periodic_failures:
            problematic_hours = periodic_failures['problematic_hours']
            if problematic_hours:
                recommendations.append("Review scheduled tasks and maintenance windows to reduce impact during high-error time periods")
        
        # Dependency correlation recommendations
        if dependency_correlations and 'likely_dependencies' in dependency_correlations:
            dependencies = dependency_correlations['likely_dependencies']
            if dependencies:
                recommendations.append("Implement health checks and circuit breakers for critical dependencies")
                recommendations.append("Consider implementing fallback mechanisms for frequently failing dependencies")
        
        # General recommendations
        recommendations.append("Set up automated alerts based on the identified error patterns and thresholds")
        recommendations.append("Implement comprehensive logging with contextual information for better root cause analysis")
        
        return recommendations

    def check_api_health(self) -> Dict[str, Any]:
        """
        Perform a real-time health check of the API endpoints
        
        Returns:
            Dict with health check results
        """
        # Load logs to identify endpoints
        df = self.load_logs()
        
        if df.empty:
            return {'status': 'error', 'message': 'No logs available to identify endpoints'}
        
        # Extract unique endpoints and methods
        endpoints = df[['endpoint', 'method']].drop_duplicates().values.tolist()
        
        # Perform health checks
        health_results = []
        overall_status = 'healthy'
        
        base_url = "http://127.0.0.1:8000"  # Assuming local deployment
        
        for endpoint, method in endpoints:
            try:
                url = f"{base_url}{endpoint}"
                
                # Make test request
                if method in ['GET', 'DELETE']:
                    response = requests.request(method, url, timeout=5)
                else:
                    # For POST/PUT, include a minimal payload
                    test_payload = {'health_check': True}
                    response = requests.request(method, url, json=test_payload, timeout=5)
                
                status = 'healthy' if response.status_code < 400 else 'unhealthy'
                if status == 'unhealthy':
                    overall_status = 'unhealthy'
                
                health_results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': response.status_code,
                    'response_time_ms': response.elapsed.total_seconds() * 1000,
                    'status': status
                })
            except requests.exceptions.RequestException as e:
                health_results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'status': 'error',
                    'error_message': str(e)
                })
                overall_status = 'unhealthy'
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status,
            'endpoint_health': health_results
        }

def main():
    """Main function to run the API root cause analyzer"""
    # Initialize Root Cause Analyzer
    analyzer = APIRootCauseAnalyzer()
    
    # Generate failure analysis report
    failure_report = analyzer.generate_failure_report()
    
    # Optionally perform a health check
    health_check = analyzer.check_api_health()
    
    # Print summary
    print("\n=== API Failure Root Cause Analysis ===")
    
    if 'total_requests' in failure_report:
        print(f"Total Requests: {failure_report['total_requests']}")
        print(f"Error Requests: {failure_report['error_requests']}")
        print(f"Error Rate: {failure_report['error_rate']:.2%}")
    
    if 'insights' in failure_report and failure_report['insights']:
        print("\nKey Insights:")
        for i, insight in enumerate(failure_report['insights'], 1):
            print(f"{i}. {insight}")
    
    if 'recommended_actions' in failure_report and failure_report['recommended_actions']:
        print("\nRecommended Actions:")
        for i, action in enumerate(failure_report['recommended_actions'], 1):
            print(f"{i}. {action}")
    
    print("\n=== API Health Check ===")
    print(f"Overall Status: {health_check['overall_status'].upper()}")
    
    unhealthy_endpoints = [e for e in health_check.get('endpoint_health', []) if e['status'] != 'healthy']
    if unhealthy_endpoints:
        print("\nUnhealthy Endpoints:")
        for endpoint in unhealthy_endpoints:
            print(f"- {endpoint['method']} {endpoint['endpoint']}: {endpoint.get('status_code', 'N/A')} ({endpoint['status']})")

if __name__ == "__main__":
    main()