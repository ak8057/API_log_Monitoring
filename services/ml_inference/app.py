from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pathlib import Path
import datetime as dt
import json
import logging
import os

import joblib
import numpy as np
import pandas as pd
import requests
from elasticsearch import Elasticsearch
from tensorflow.keras.models import load_model


load_dotenv()

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SERVICE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SERVICE_DIR.parents[1]
DEFAULT_LOG_FILE = REPO_ROOT / "dock" / "logs" / "api_logs.json"

LOG_FILE = Path(os.getenv("ML_LOG_FILE", str(DEFAULT_LOG_FILE)))
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_USERNAME = os.getenv("ES_USERNAME", "elastic")
ES_PASSWORD = os.getenv("ES_PASSWORD", "")
MODEL_DIR = Path(os.getenv("ML_MODEL_DIR", str(SERVICE_DIR)))

es = None
try:
    es = Elasticsearch(ES_HOST, basic_auth=(ES_USERNAME, ES_PASSWORD) if ES_PASSWORD else None)
except Exception as exc:
    logger.warning("Elasticsearch client unavailable: %s", exc)


def _load_artifact(path: Path):
    if not path.exists():
        logger.warning("Artifact missing: %s", path)
        return None
    return path


MODEL_PATHS = {
    "Spike_1": (MODEL_DIR / "lstm_anomaly_model.h5", MODEL_DIR / "scaler.save"),
    "Spike_2": (MODEL_DIR / "h2.h5", MODEL_DIR / "scaler2.save"),
    "Spike_3": (MODEL_DIR / "h3.h5", MODEL_DIR / "scaler3.save"),
}


def load_pair(model_path: Path, scaler_path: Path):
    model = load_model(str(model_path)) if model_path.exists() else None
    scaler = joblib.load(str(scaler_path)) if scaler_path.exists() else None
    return model, scaler


def read_logs(log_file: Path) -> pd.DataFrame:
    if not log_file.exists():
        return pd.DataFrame()
    with log_file.open("r") as handle:
        logs = [json.loads(line) for line in handle if line.strip()]
    if not logs:
        return pd.DataFrame()
    frame = pd.DataFrame(logs)
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    return frame


def create_sequences(data: np.ndarray, time_steps: int = 30):
    sequences = []
    for index in range(len(data) - time_steps):
        sequences.append(data[index : index + time_steps])
    return np.array(sequences)


def extract_features_model1(df: pd.DataFrame):
    return pd.DataFrame({"response_time_ms": df["response_time_ms"]})


def extract_features_model2(df: pd.DataFrame):
    return pd.DataFrame(
        {
            "hour": pd.to_datetime(df["timestamp"]).dt.hour,
            "is_error": (df["status_code"] >= 400).astype(int),
            "request_size": df.apply(
                lambda row: len(str(row["request_body"])) if isinstance(row.get("request_body"), dict) else 0,
                axis=1,
            ),
            "is_onprem": (df.get("environment", "unknown") == "on-prem").astype(int),
        }
    )


def extract_features_model3(df: pd.DataFrame):
    return pd.DataFrame(
        {
            "method": df.get("method", "unknown"),
            "endpoint": df.get("endpoint", "unknown"),
            "environment": df.get("environment", "unknown"),
            "client_ip": df.get("client_ip", "unknown"),
            "response_time_ms": df.get("response_time_ms", 0),
            "hour": pd.to_datetime(df["timestamp"]).dt.hour,
            "is_error": (df["status_code"] >= 400).astype(int),
            "is_onprem": (df.get("environment", "unknown") == "on-prem").astype(int),
        }
    )


def send_to_elasticsearch(document: dict, index_name: str):
    if es is None:
        return None
    try:
        return es.index(index=index_name, document=document)
    except Exception as exc:
        logger.error("Elasticsearch indexing failed: %s", exc)
        return None


def process_with_model(model, scaler, anomaly_label, feature_fn, frame: pd.DataFrame):
    if model is None or scaler is None or frame.empty:
        return pd.DataFrame()

    features = feature_fn(frame)

    if anomaly_label == "Spike_1":
        scaled = scaler.transform(features)
        time_steps = 30
        if len(scaled) < time_steps:
            return pd.DataFrame()
        sequences = create_sequences(scaled, time_steps)
        predictions = model.predict(sequences)
        truth = scaled[time_steps:]
        errors = np.abs(predictions.flatten() - truth.flatten())
        copy = frame.iloc[time_steps:].copy()
        copy[anomaly_label] = errors > float(os.getenv("ML_THRESHOLD", "0.15"))
        copy["anomaly_score"] = errors
        return copy

    if anomaly_label == "Spike_2":
        scaled = scaler.transform(features)
        crash_probs = model.predict(scaled)
        copy = frame.copy()
        copy[anomaly_label] = crash_probs > 0.5
        copy["crash_probability"] = crash_probs
        return copy

    if anomaly_label == "Spike_3":
        scaled = scaler.transform(features)
        failure_probs = model.predict(scaled)
        copy = frame.copy()
        copy[anomaly_label] = failure_probs > 0.5
        copy["failure_probability"] = failure_probs
        return copy

    return pd.DataFrame()


@app.get("/")
def health():
    return jsonify(
        {
            "status": "ready",
            "log_file": str(LOG_FILE),
            "model_dir": str(MODEL_DIR),
            "timestamp": dt.datetime.utcnow().isoformat(),
        }
    )


@app.post("/predict")
def predict_anomaly():
    payload = request.get_json(silent=True) or {}
    source_type = payload.get("source_type", "json_data")

    if source_type == "json_data" and payload.get("logs"):
        frame = pd.DataFrame(payload["logs"])
    else:
        frame = read_logs(LOG_FILE)

    if frame.empty:
        return jsonify({"status": "empty", "message": "No logs available"}), 200

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame = frame.sort_values("timestamp")

    outputs = []
    for label, (model_path, scaler_path) in MODEL_PATHS.items():
        model, scaler = load_pair(_load_artifact(model_path), _load_artifact(scaler_path))
        if label == "Spike_1":
            result = process_with_model(model, scaler, label, extract_features_model1, frame)
        elif label == "Spike_2":
            result = process_with_model(model, scaler, label, extract_features_model2, frame)
        else:
            result = process_with_model(model, scaler, label, extract_features_model3, frame)

        if result.empty:
            continue

        output_file = MODEL_DIR / f"{label.lower()}_results.json"
        result = result.where(pd.notnull(result), None)
        result.to_json(output_file, orient="records", lines=True)

        for _, row in result.iterrows():
            row_dict = row.to_dict()
            if any(key.startswith("Spike_") and row_dict.get(key) for key in row_dict):
                row_dict["@timestamp"] = dt.datetime.utcnow().isoformat()
                send_to_elasticsearch(row_dict, "api_logs_ml_results")

        outputs.append(str(output_file))

    return jsonify({"status": "success", "output_files": outputs})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("ML_SERVICE_PORT", "5000")), debug=True)