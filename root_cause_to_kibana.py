import os
import sys
import json
import argparse
import logging
from datetime import datetime
import time

# Import root cause analyzer and Kibana integration
from root_cause_analyzer import APIRootCauseAnalyzer
from kibana_integration import KibanaRootCauseIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('kibana_integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('kibana_integration')

def load_config(config_path):
    """
    Load configuration file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    default_config = {
        'log_file': '/Users/abhaykumar/codeit/projects/Machine_Learning/API_LOG/dock/logs/api_logs.json',
        'elasticsearch': {
            'host': 'http://localhost:9200',
            'username': 'elastic',
            'password': '',
            'index_prefix': 'api-monitoring'
        },
        'kibana': {
            'host': 'http://localhost:5601',
            'dashboard_name': 'API Root Cause Analysis'
        },
        'monitoring': {
            'error_threshold': 0.2,
            'response_time_threshold': 1500,
            'check_interval': 300
        }
    }
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                
                # Merge user config with default config
                if 'elasticsearch' in user_config:
                    default_config['elasticsearch'].update(user_config['elasticsearch'])
                if 'kibana' in user_config:
                    default_config['kibana'].update(user_config['kibana'])
                if 'monitoring' in user_config:
                    default_config['monitoring'].update(user_config['monitoring'])
                if 'log_file' in user_config:
                    default_config['log_file'] = user_config['log_file']
        else:
            logger.warning(f"Configuration file {config_path} not found, using defaults")
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
    
    return default_config

def run_root_cause_analysis(config, args):
    """
    Run root cause analysis
    
    Args:
        config: Configuration dictionary
        args: Command line arguments
        
    Returns:
        Root cause analysis report
    """
    logger.info("Running root cause analysis")
    
    # Determine log file path
    log_file = args.log_file or config['log_file']
    
    # Determine error threshold
    error_threshold = args.threshold or config['monitoring']['error_threshold']
    
    # Initialize analyzer
    analyzer = APIRootCauseAnalyzer(
        log_file=log_file,
        error_threshold=error_threshold
    )
    
    # Generate report
    report = analyzer.generate_failure_report()
    
    # Run health check
    health_check = analyzer.check_api_health()
    
    # Add health check to report
    if report and health_check:
        report['health_check'] = health_check
    
    # Save report to file
    report_filename = f'api_failure_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"Root cause analysis report saved to {report_filename}")
    
    return report, report_filename

def send_to_kibana(report, config, args):
    """
    Send root cause analysis data to Kibana
    
    Args:
        report: Root cause analysis report
        config: Configuration dictionary
        args: Command line arguments
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Sending root cause analysis data to Kibana")
    
    # Get Elasticsearch configuration
    es_config = config['elasticsearch']
    
    # Override with command line arguments if provided
    if args.es_host:
        es_config['host'] = args.es_host
    if args.es_username:
        es_config['username'] = args.es_username
    if args.es_password:
        es_config['password'] = args.es_password
    if args.index_prefix:
        es_config['index_prefix'] = args.index_prefix
    
    # Get Kibana configuration
    kibana_config = config['kibana']
    
    # Override with command line arguments if provided
    dashboard_name = args.dashboard_name or kibana_config.get('dashboard_name', 'API Root Cause Analysis')
    
    # Initialize Kibana integration
    integration = KibanaRootCauseIntegration(
        es_host=es_config['host'],
        es_username=es_config['username'],
        es_password=es_config['password'],
        index_prefix=es_config['index_prefix'],
        dashboard_name=dashboard_name,
        create_visualizations=args.create_dashboard
    )
    
    # Create indices
    if not integration.create_indices():
        logger.error("Failed to create Elasticsearch indices")
        return False
    
    # Index root cause data
    if not integration.index_root_cause_data(report):
        logger.error("Failed to index root cause data")
        return False
    
    # Generate dashboard export file if requested
    if args.create_dashboard:
        if not integration.generate_kibana_dashboard_export():
            logger.error("Failed to generate Kibana dashboard export file")
            return False
        
        # Try to import dashboard to Kibana
        integration.import_dashboard_to_kibana()
    
    logger.info("Root cause data successfully sent to Kibana")
    
    # Log Kibana dashboard URL
    kibana_url = es_config['host'].replace('9200', '5601')
    if not kibana_url.endswith('/'):
        kibana_url += '/'
    
    logger.info(f"You can view the dashboard at: {kibana_url}app/dashboards#/view/api-root-cause-dashboard")
    
    return True

def schedule_kibana_integration(config, args, interval=None):
    """
    Schedule periodic Kibana integration
    
    Args:
        config: Configuration dictionary
        args: Command line arguments
        interval: Integration interval in seconds (default: from config)
        
    Returns:
        None
    """
    # Determine interval
    if interval is None:
        interval = config['monitoring'].get('check_interval', 300)
    
    logger.info(f"Scheduling Kibana integration every {interval} seconds")
    
    try:
        while True:
            # Run analysis
            report, _ = run_root_cause_analysis(config, args)
            
            # Send to Kibana
            if report:
                send_to_kibana(report, config, args)
            
            # Wait for next integration
            logger.info(f"Waiting {interval} seconds until next integration")
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Kibana integration stopped by user")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Root Cause to Kibana Integration')
    parser.add_argument('--log-file', type=str, help='Path to API logs')
    parser.add_argument('--config', type=str, default='monitor_config.json', help='Path to configuration file')
    parser.add_argument('--es-host', type=str, help='Elasticsearch host URL')
    parser.add_argument('--es-username', type=str, help='Elasticsearch username')
    parser.add_argument('--es-password', type=str, help='Elasticsearch password')
    parser.add_argument('--index-prefix', type=str, help='Index prefix for Elasticsearch')
    parser.add_argument('--dashboard-name', type=str, help='Kibana dashboard name')
    parser.add_argument('--analyze-only', action='store_true', help='Only perform analysis without sending to Kibana')
    parser.add_argument('--create-dashboard', action='store_true', help='Create/update Kibana dashboard')
    parser.add_argument('--threshold', type=float, help='Error threshold for analysis')
    parser.add_argument('--schedule', action='store_true', help='Schedule periodic integration')
    parser.add_argument('--interval', type=int, help='Integration interval in seconds')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Schedule periodic integration if requested
    if args.schedule:
        schedule_kibana_integration(config, args, args.interval)
        return
    
    # Run root cause analysis
    report, report_filename = run_root_cause_analysis(config, args)
    
    if not report:
        logger.error("Root cause analysis failed")
        return 1
    
    # Print summary
    if 'insights' in report and report['insights']:
        logger.info("Key insights:")
        for i, insight in enumerate(report['insights'][:5], 1):
            logger.info(f"{i}. {insight}")
    
    if 'recommended_actions' in report and report['recommended_actions']:
        logger.info("Recommended actions:")
        for i, action in enumerate(report['recommended_actions'][:5], 1):
            logger.info(f"{i}. {action}")
    
    # Send to Kibana if not analyze-only
    if not args.analyze_only:
        if send_to_kibana(report, config, args):
            logger.info("Kibana integration completed successfully")
        else:
            logger.error("Kibana integration failed")
            return 1
    
    logger.info("Root cause to Kibana integration completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())