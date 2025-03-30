import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const API_URL = "http://127.0.0.1:8000/logs";

export default function LogsChart() {
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    fetch(API_URL)
      .then((response) => response.json())
      .then((data) => {
        console.log("Logs:", data);
        // Transform data for chart
        const formattedData = data.map((log) => ({
          timestamp: new Date(log.timestamp).toLocaleTimeString(),
          request_count: 1, // Since each log is a request
        }));
        setChartData(formattedData);
      })
      .catch((error) => console.error("Error fetching logs:", error));
  }, []);

  return (
    <div style={{ width: "100%", height: 400 }}>
      <h2>API Request Trend</h2>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <XAxis dataKey="timestamp" />
          <YAxis />
          <Tooltip />
          <Line
            type="monotone"
            dataKey="request_count"
            stroke="#8884d8"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
