import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest

# Load API logs
def load_logs():
    logs = []
    with open("api_logs.json", "r") as f:
        for line in f:
            logs.append(json.loads(line.strip()))
    return pd.DataFrame(logs)

df = load_logs()
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Simulating response times (since real logs don’t have them)
df["response_time_ms"] = np.random.normal(loc=200, scale=50, size=len(df))

# Train anomaly detection model
model = IsolationForest(contamination=0.05)
df["anomaly"] = model.fit_predict(df[["response_time_ms"]])

# Plot anomalies
plt.figure(figsize=(10,5))
sns.scatterplot(x=df["timestamp"], y=df["response_time_ms"], hue=df["anomaly"], palette={1: "blue", -1: "red"})
plt.xlabel("Time")
plt.ylabel("Response Time (ms)")
plt.title("Anomaly Detection in API Response Time")
plt.xticks(rotation=45)
plt.show()
