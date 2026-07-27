# 🛡️ AI-Powered API Monitoring & Anomaly Detection System

<h2 id="index">📖 Index</h2>

> 🚀 Developed by Team VCHAMPS | Finalists at Barclays Hack-O-Hire 2025 (Generative AI Track)

## 📌 Problem Statement
APIs are the backbone of modern digital platforms. However, failures, security issues, and performance degradation due to poor monitoring can lead to serious consequences including:
- Downtime and financial loss
- Delayed incident response
- Inefficient debugging
- Missed security breaches

  <img width="696" height="222" alt="Image" src="https://github.com/user-attachments/assets/a27390a3-034f-4281-bbac-8475b2b8161f" />

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
- **Kibana**.

### 🤖 Machine Learning
- **Isolation Forest, LSTM, Autoencoders**
- **TensorFlow**, **scikit-learn**


## 🔧 Architecture Overview

1. **Log Generation & Collection**  
   → Flask / Node.js apps log data via Filebeat

2. **Log Storage & Preprocessing**  
   → Processed through Logstash → Indexed in Elasticsearch

3. **ML Feature Extraction & Anomaly Detection**  
   → Structured logs converted to datasets  
   → Detected via ML models (Isolation Forest, LSTM, BERT for unknown logs)

4. **Real-Time Monitoring & Alerting**    
   → Dashboards via Kibana.

## 🎥 Demo
- https://drive.google.com/file/d/1GZNg6zhviRN5gu8I-auiR7ULnyhWvgx7/view?usp=sharing

This video provides a demonstration of an anomaly detection application designed for log monitoring. The process flow is as follows:
**Log Generation** : The process begins by creating scenarios that generate logs live. These logs are saved into a file named api_logs.json.

**Machine Learning Analysis** : The saved logs are processed by three machine learning models, which act as APIs within a Flask server. These models analyze the input and append their findings—such as crash probability and spike status—to the data.

**Data Pipeline** : The logs are retrieved via Filebeat and then ingested into Elasticsearch by way of Logstash.

**Visualization** : Data is displayed in Kibana, where an interface and dashboard have been established to visualize various metrics, such as record counts and response times. This includes graphs depicting the machine learning model outputs, such as pie charts showing current spike statuses.

## 👥 Team VCHAMPS
- **Abhay Kumar** – RA2311003010980 – ak8057@srmist.edu.in  
- **Akshit Bhatt** – RA2311003010979 – ab3675@srmist.edu.in  
- **Akshat Baranwal** – RA2311003010956 – ab6043@srmist.edu.in  
- **Vishnu Gupta** – RA2311003010926 – vg0832@srmist.edu.in  
- **Aarshiya Das** – RA2311003010938 – ad1445@srmist.edu.in  

---

> 🏁 **Built with passion at Barclays Hack-O-Hire 2025**



![Image](https://github.com/user-attachments/assets/f80c8e63-c0b5-4ddb-97b0-2b615c85b207)


<div align="right">
  <b><a href="#index">↥ Back To Top</a></b>
</div>
