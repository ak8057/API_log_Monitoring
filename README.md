# 🛡️ AI-Powered API Monitoring & Anomaly Detection System

> 🚀 Developed by Team VCHAMPS | Finalists at Barclays Hack-O-Hire 2025 (Generative AI Track)

## 📌 Problem Statement
APIs are the backbone of modern digital platforms. However, failures, security issues, and performance degradation due to poor monitoring can lead to serious consequences including:
- Downtime and financial loss
- Delayed incident response
- Inefficient debugging
- Missed security breaches

## 💡 Our Solution
An AI-driven, scalable monitoring and anomaly detection system for large-scale distributed platforms that:
- Monitors API behavior in real-time
- Detects anomalies using ML (Isolation Forest, LSTM, Autoencoders)
- Automates alerting and response
- Visualizes insights using ELK stack & Grafana

## 🧠 Key Features
- ✅ Real-Time Log Monitoring
- 🔍 ML-Based Anomaly Detection
- 📊 Interactive Dashboards (Kibana, Grafana)
- 📬 Automated Alerts (Email/Slack/Prometheus)
- 🔁 Continuous Learning with Feedback Loop

## 🧰 Tech Stack

### 🗂 Log Collection & Processing
- **Filebeat, Logstash, Kafka** for ingestion
- **Elasticsearch** for storage
- **MongoDB** for structured logging

### 📈 Visualization & Monitoring
- **Kibana**, **Grafana**, **Streamlit** dashboards

### 🤖 Machine Learning
- **Isolation Forest, LSTM, Autoencoders**
- **TensorFlow**, **scikit-learn**
- **MLflow** for model versioning

### ⚙️ Deployment
- **Docker**, **Kubernetes**, **FastAPI**
- **AWS Lambda** for scalability

## 🔧 Architecture Overview

1. **Log Generation & Collection**  
   → Flask / Node.js apps log data via Filebeat

2. **Log Storage & Preprocessing**  
   → Processed through Logstash → Indexed in Elasticsearch

3. **ML Feature Extraction & Anomaly Detection**  
   → Structured logs converted to datasets  
   → Detected via ML models (Isolation Forest, LSTM, BERT for unknown logs)

4. **Real-Time Monitoring & Alerting**  
   → Alerts via Prometheus/Email/Slack  
   → Dashboards via Kibana, Grafana

5. **Continuous Learning Loop**  
   → Feedback improves model accuracy over time

## 📊 Impact
- 99.9% API uptime achieved
- 40% drop in response failures
- 70% improvement in fraud/anomaly detection
- 30% faster root cause analysis

## 🎥 Demo
- [Working Demo 1](https://drive.google.com/file/d/1D-ewuthfm8MZes7tB7WjdHTKThHdDHb1/view?usp=sharing)
- [Working Demo 2](https://drive.google.com/file/d/16ME_3w9uLtfkpoVn3vj4BX7OPJAfSvqn/view?usp=sharing)

## 👥 Team VCHAMPS
- **Abhay Kumar** – RA2311003010980 – ak8057@srmist.edu.in  
- **Akshit Bhatt** – RA2311003010979 – ab3675@srmist.edu.in  
- **Akshat Baranwal** – RA2311003010956 – ab6043@srmist.edu.in  
- **Vishnu Gupta** – RA2311003010926 – vg0832@srmist.edu.in  
- **Aarshiya Das** – RA2311003010938 – ad1445@srmist.edu.in  

---

> 🏁 **Built with passion at Barclays Hack-O-Hire 2025**


<img width="696" height="222" alt="Image" src="https://github.com/user-attachments/assets/a27390a3-034f-4281-bbac-8475b2b8161f" />


![Image](https://github.com/user-attachments/assets/f80c8e63-c0b5-4ddb-97b0-2b615c85b207)
