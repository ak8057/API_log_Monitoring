import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
import requests
from datetime import datetime, timedelta

class JourneyPredictor:
    def __init__(self, 
                 log_file='/Users/abhaykumar/codeit/projects/Machine_Learning/API_LOG/dock/logs/api_logs.json', 
                 es_host='http://localhost:9200', 
                 es_index='journey-predictions'):
        """
        Initialize Journey Predictor for multi-environment analysis
        
        Args:
            log_file (str): Path to API logs
            es_host (str): Elasticsearch host
            es_index (str): Elasticsearch index for predictions
        """
        self.log_file = log_file
        self.es_host = es_host
        self.es_index = es_index

    def load_logs(self):
        """
        Load logs from JSON file
        
        Returns:
            pd.DataFrame: Processed logs
        """
        try:
            with open(self.log_file, 'r') as f:
                logs = [json.loads(line.strip()) for line in f]
            
            df = pd.DataFrame(logs)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except Exception as e:
            print(f"Error loading logs: {e}")
            return pd.DataFrame()

    def extract_journey_features(self, df):
        """
        Extract features for journey prediction
        
        Args:
            df (pd.DataFrame): Logs dataframe
        
        Returns:
            pd.DataFrame: Extracted features
        """
        # Group logs by potential journey correlations
        journey_features = []
        
        # Group by similar request characteristics
        grouped = df.groupby(['method', 'endpoint', 'environment'])
        
        for (method, endpoint, environment), group in grouped:
            features = {
                'method': method,
                'endpoint': endpoint,
                'environment': environment,
                'avg_response_time': group['response_time_ms'].mean(),
                'response_time_std': group['response_time_ms'].std(),
                'error_rate': (group['status_code'] >= 400).mean(),
                'total_requests': len(group),
                'unique_status_codes': group['status_code'].nunique(),
                'timestamp_spread': (group['timestamp'].max() - group['timestamp'].min()).total_seconds()
            }
            journey_features.append(features)
        
        return pd.DataFrame(journey_features)

    def predict_journey_anomalies(self, features):
        """
        Predict potential issues in request journeys
        
        Args:
            features (pd.DataFrame): Journey features
        
        Returns:
            pd.DataFrame: Anomaly predictions
        """
        # Prepare data for anomaly detection
        if features.empty:
            return features

        # Select numerical features for anomaly detection
        numerical_features = [
            'avg_response_time', 
            'response_time_std', 
            'error_rate', 
            'total_requests', 
            'unique_status_codes', 
            'timestamp_spread'
        ]
        
        # Scale features
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features[numerical_features])
        
        # Use Isolation Forest for anomaly detection
        clf = IsolationForest(contamination=0.1, random_state=42)
        features['anomaly_score'] = clf.fit_predict(scaled_features)
        
        # Mark anomalies
        features['is_anomalous'] = features['anomaly_score'] == -1
        
        return features

    def index_predictions_to_elasticsearch(self, predictions):
        """
        Index journey predictions to Elasticsearch
        
        Args:
            predictions (pd.DataFrame): Predicted journey anomalies
        """
        # Prepare bulk indexing request
        bulk_body = []
        
        for _, row in predictions[predictions['is_anomalous']].iterrows():
            # Prepare document for indexing
            doc = {
                'timestamp': datetime.now().isoformat(),
                'method': row['method'],
                'endpoint': row['endpoint'],
                'environment': row['environment'],
                'avg_response_time': row['avg_response_time'],
                'error_rate': row['error_rate'],
                'total_requests': row['total_requests'],
                'anomaly_prediction': {
                    'score': row['anomaly_score'],
                    'potential_issues': self._generate_issue_insights(row)
                }
            }
            
            # Prepare bulk index operation
            bulk_body.append(json.dumps({"index": {}}))
            bulk_body.append(json.dumps(doc))
        
        # Perform bulk indexing
        if bulk_body:
            try:
                response = requests.post(
                    f"{self.es_host}/{self.es_index}/_bulk",
                    data="\n".join(bulk_body) + "\n",
                    headers={"Content-Type": "application/x-ndjson"}
                )
                response.raise_for_status()
                print("Successfully indexed predictions to Elasticsearch")
            except Exception as e:
                print(f"Error indexing to Elasticsearch: {e}")

    def _generate_issue_insights(self, row):
        """
        Generate potential issue insights for an anomalous journey
        
        Args:
            row (pd.Series): Anomalous journey features
        
        Returns:
            List of potential issue descriptions
        """
        insights = []
        
        # High response time insights
        if row['avg_response_time'] > 1000:  # ms
            insights.append(f"Potential performance bottleneck: Avg response time {row['avg_response_time']:.2f}ms")
        
        # High error rate insights
        if row['error_rate'] > 0.3:  # 30% error rate
            insights.append(f"High error rate detected: {row['error_rate']:.2%}")
        
        # Low request volume with high variability
        if row['total_requests'] < 10 and row['response_time_std'] > 500:
            insights.append("Inconsistent performance with low request volume")
        
        return insights

    def predict_multi_environment_journeys(self):
        """
        Main method to predict potential issues in multi-environment journeys
        """
        # Load logs
        df = self.load_logs()
        
        if df.empty:
            print("No logs available for prediction")
            return
        
        # Extract journey features
        journey_features = self.extract_journey_features(df)
        
        # Predict anomalies
        predictions = self.predict_journey_anomalies(journey_features)
        
        # Index predictions to Elasticsearch
        self.index_predictions_to_elasticsearch(predictions)
        
        # Print summary of anomalies
        print("\n--- Journey Anomaly Predictions ---")
        anomalies = predictions[predictions['is_anomalous']]
        print(f"Total Anomalies Detected: {len(anomalies)}")
        
        for _, anomaly in anomalies.iterrows():
            print(f"\nMethod: {anomaly['method']}")
            print(f"Endpoint: {anomaly['endpoint']}")
            print(f"Environment: {anomaly['environment']}")
            print(f"Avg Response Time: {anomaly['avg_response_time']:.2f}ms")
            print(f"Error Rate: {anomaly['error_rate']:.2%}")

def main():
    # Initialize and run journey predictor
    predictor = JourneyPredictor()
    predictor.predict_multi_environment_journeys()

if __name__ == "__main__":
    main()
