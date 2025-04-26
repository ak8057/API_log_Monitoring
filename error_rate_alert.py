

import os
import json
import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List

class ErrorRateAlerter:
    def __init__(self, config_path='alert_config.json'):
        """
        Initialize alerting system with configurable channels
        
        Args:
            config_path (str): Path to alerting configuration
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s: %(message)s',
            filename='error_rate_alerts.log'
        )
        self.logger = logging.getLogger(__name__)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load alerting configuration
        
        Args:
            config_path (str): Path to config file
        
        Returns:
            Dict with alert configuration
        """
        default_config = {
            "email_alerts": {
                "enabled": False,
                "smtp_host": "",
                "smtp_port": 587,
                "smtp_username": "",
                "smtp_password": "",
                "sender_email": "",
                "recipient_emails": []
            },
            "slack_alerts": {
                "enabled": False,
                "webhook_url": ""
            },
            "pagerduty_alerts": {
                "enabled": False,
                "integration_key": ""
            },
            "telegram_alerts": {
                "enabled": False,
                "bot_token": "",
                "chat_ids": []
            }
        }
        
        try:
            # Try to load existing config
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    # Merge user config with default config
                    default_config.update(user_config)
            else:
                # Create default config file if it doesn't exist
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
            
            return default_config
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return default_config

    def send_email_alert(self, subject: str, message: str):
        """
        Send email alert
        
        Args:
            subject (str): Email subject
            message (str): Email body
        """
        email_config = self.config.get('email_alerts', {})
        
        if not email_config.get('enabled', False):
            return
        
        try:
            # Create message
            email_msg = MIMEMultipart()
            email_msg['From'] = email_config['sender_email']
            email_msg['To'] = ', '.join(email_config['recipient_emails'])
            email_msg['Subject'] = subject
            
            # Attach message body
            email_msg.attach(MIMEText(message, 'plain'))
            
            # Send email
            with smtplib.SMTP(email_config['smtp_host'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['smtp_username'], email_config['smtp_password'])
                server.send_message(email_msg)
            
            self.logger.info("Email alert sent successfully")
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")

    def send_slack_alert(self, message: str):
        """
        Send Slack webhook alert
        
        Args:
            message (str): Alert message
        """
        slack_config = self.config.get('slack_alerts', {})
        
        if not slack_config.get('enabled', False):
            return
        
        try:
            payload = {
                "text": message
            }
            
            response = requests.post(
                slack_config['webhook_url'], 
                json=payload
            )
            
            if response.status_code == 200:
                self.logger.info("Slack alert sent successfully")
            else:
                self.logger.error(f"Failed to send Slack alert: {response.text}")
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")

    def send_pagerduty_alert(self, title: str, message: str):
        """
        Send PagerDuty incident alert
        
        Args:
            title (str): Alert title
            message (str): Alert message
        """
        pagerduty_config = self.config.get('pagerduty_alerts', {})
        
        if not pagerduty_config.get('enabled', False):
            return
        
        try:
            payload = {
                "routing_key": pagerduty_config['integration_key'],
                "event_action": "trigger",
                "payload": {
                    "summary": title,
                    "severity": "critical",
                    "source": "API Error Rate Monitor"
                }
            }
            
            response = requests.post(
                "https://events.pagerduty.com/v2/enqueue", 
                json=payload
            )
            
            if response.status_code == 202:
                self.logger.info("PagerDuty alert sent successfully")
            else:
                self.logger.error(f"Failed to send PagerDuty alert: {response.text}")
        except Exception as e:
            self.logger.error(f"Failed to send PagerDuty alert: {e}")

    def send_telegram_alert(self, message: str):
        """
        Send Telegram bot alert
        
        Args:
            message (str): Alert message
        """
        telegram_config = self.config.get('telegram_alerts', {})
        
        if not telegram_config.get('enabled', False):
            return
        
        try:
            for chat_id in telegram_config.get('chat_ids', []):
                payload = {
                    "chat_id": chat_id,
                    "text": message
                }
                
                response = requests.post(
                    f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage", 
                    json=payload
                )
                
                if response.status_code == 200:
                    self.logger.info(f"Telegram alert sent to {chat_id} successfully")
                else:
                    self.logger.error(f"Failed to send Telegram alert: {response.text}")
        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")

    def send_comprehensive_alert(self, error_report: Dict[str, Any]):
        """
        Send comprehensive alerts across multiple channels
        
        Args:
            error_report (Dict): Error rate analysis report
        """
        # Prepare alert message
        overall = error_report.get('overall_analysis', {})
        total_requests = overall.get('total_requests', 0)
        error_requests = overall.get('error_requests', 0)
        error_rate = overall.get('error_rate', 0)

        # Construct alert message
        alert_message = f"""
🚨 API Error Rate Anomaly Detected 🚨

Total Requests: {total_requests}
Error Requests: {error_requests}
Overall Error Rate: {error_rate:.2%}

Anomalous Endpoints:
"""
        # Add anomalous endpoints to message
        for endpoint, metrics in error_report.get('endpoint_analysis', {}).items():
            if metrics.get('is_anomalous'):
                alert_message += f"- {endpoint}: {metrics['error_rate']:.2%} error rate\n"

        # Send alerts through configured channels
        alert_title = f"API Error Rate Alert - {error_rate:.2%} Errors"
        
        # Email Alert
        self.send_email_alert(alert_title, alert_message)
        
        # Slack Alert
        self.send_slack_alert(alert_message)
        
        # PagerDuty Alert
        self.send_pagerduty_alert(alert_title, alert_message)
        
        # Telegram Alert
        self.send_telegram_alert(alert_message)

def main():
    # Import the error rate monitor
    from error_rate_monitor import ErrorRateMonitor
    
    # Initialize Error Rate Monitor
    error_monitor = ErrorRateMonitor()
    
    # Generate error report
    error_report = error_monitor.generate_error_report()
    
    # Check if there are anomalies
    overall = error_report.get('overall_analysis', {})
    has_anomalies = any(
        metrics.get('is_anomalous', False) 
        for metrics in [
            overall,
            *error_report.get('endpoint_analysis', {}).values()
        ]
    )
    
    # Send alerts if anomalies exist
    if has_anomalies:
        alerter = ErrorRateAlerter()
        alerter.send_comprehensive_alert(error_report)
        print("Alerts sent for detected anomalies.")
    else:
        print("No anomalies detected. No alerts sent.")

if __name__ == "__main__":
    main()