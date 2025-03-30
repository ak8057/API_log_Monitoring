import React, { useState, useEffect  , useRef } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  Clock,
  AlertTriangle,
  Activity,
  Server,
  BarChart as BarChartIcon,
  PieChart as PieChartIcon,
  RefreshCw,
} from "lucide-react";

// Real API data fetching
const Dashboard = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshInterval, setRefreshInterval] = useState(5);
  const [lastRefreshed, setLastRefreshed] = useState(new Date());
   const logsEndRef = useRef(null);


  // Color configurations
  const COLORS = {
    success: "#10b981",
    error: "#ef4444",
    warning: "#f59e0b",
    info: "#3b82f6",
    successLight: "#d1fae5",
    errorLight: "#fee2e2",
    warningLight: "#fef3c7",
    infoLight: "#dbeafe",
    primary: "#6366f1",
    secondary: "#8b5cf6",
    neutral: "#a3a3a3",
  };

  // Status code colors
  const getStatusCodeColor = (code) => {
    if (code < 300) return COLORS.success;
    if (code < 400) return COLORS.warning;
    if (code < 500) return COLORS.warning;
    return COLORS.error;
  };

  // Fetch log data
  const fetchLogs = async () => {
    try {
      setLoading(true);
      const response = await fetch("http://127.0.0.1:8000/logs");
      if (!response.ok) {
        throw new Error("Failed to fetch logs");
      }
      const data = await response.json();
      setLogs(Array.isArray(data) ? data : [data]); // Ensure it's an array
      setLastRefreshed(new Date());
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error("Error fetching logs:", err);
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and interval setup
  useEffect(() => {
    fetchLogs();

    const intervalId = setInterval(() => {
      fetchLogs();
    }, refreshInterval * 1000);

    return () => clearInterval(intervalId);
  }, [refreshInterval]);

  // Manual refresh
  const handleManualRefresh = () => {
    fetchLogs();
  };

  // Process log data for different visualizations
  const processData = () => {
    if (!logs || logs.length === 0) {
      return {
        timeSeriesData: [],
        statusCodeData: [],
        endpointData: [],
        methodData: [],
        responseTimeData: [],
      };
    }

    // Group logs by timestamp (hourly)
    const timeGroups = {};
    const statusCodes = {};
    const endpoints = {};
    const methods = {};
    const responseTimes = {
      "<100ms": 0,
      "100-300ms": 0,
      "300-500ms": 0,
      "500-1000ms": 0,
      ">1000ms": 0,
    };

    logs.forEach((log) => {
      // Time series grouping
      const timestamp = new Date(log.timestamp);
      const hourKey = timestamp.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });

      if (!timeGroups[hourKey]) {
        timeGroups[hourKey] = {
          time: hourKey,
          requests: 0,
          successCount: 0,
          errorCount: 0,
          totalResponseTime: 0,
        };
      }

      timeGroups[hourKey].requests++;
      if (log.status_code < 400) {
        timeGroups[hourKey].successCount++;
      } else {
        timeGroups[hourKey].errorCount++;
      }
      timeGroups[hourKey].totalResponseTime += log.response_time_ms || 0;

      // Status code distribution
      const statusCodeKey = log.status_code.toString();
      if (!statusCodes[statusCodeKey]) {
        statusCodes[statusCodeKey] = { code: log.status_code, count: 0 };
      }
      statusCodes[statusCodeKey].count++;

      // Endpoint analysis
      const path = new URL(log.url).pathname;
      if (!endpoints[path]) {
        endpoints[path] = {
          endpoint: path,
          requests: 0,
          errorCount: 0,
          totalResponseTime: 0,
        };
      }
      endpoints[path].requests++;
      if (log.status_code >= 400) {
        endpoints[path].errorCount++;
      }
      endpoints[path].totalResponseTime += log.response_time_ms || 0;

      // HTTP method distribution
      const method = log.method;
      if (!methods[method]) {
        methods[method] = { name: method, count: 0 };
      }
      methods[method].count++;

      // Response time distribution
      const responseTime = log.response_time_ms || 0;
      if (responseTime < 100) {
        responseTimes["<100ms"]++;
      } else if (responseTime < 300) {
        responseTimes["100-300ms"]++;
      } else if (responseTime < 500) {
        responseTimes["300-500ms"]++;
      } else if (responseTime < 1000) {
        responseTimes["500-1000ms"]++;
      } else {
        responseTimes[">1000ms"]++;
      }
    });

    // Convert grouped data to arrays and calculate averages
    const timeSeriesData = Object.values(timeGroups).map((group) => ({
      time: group.time,
      requests: group.requests,
      successRate:
        group.requests > 0
          ? ((group.successCount / group.requests) * 100).toFixed(1)
          : 0,
      avgResponseTime:
        group.requests > 0
          ? Math.round(group.totalResponseTime / group.requests)
          : 0,
    }));

    const statusCodeData = Object.values(statusCodes);

    const endpointData = Object.values(endpoints).map((endpoint) => ({
      endpoint: endpoint.endpoint,
      requests: endpoint.requests,
      avgResponseTime:
        endpoint.requests > 0
          ? Math.round(endpoint.totalResponseTime / endpoint.requests)
          : 0,
      errorRate:
        endpoint.requests > 0
          ? Math.round((endpoint.errorCount / endpoint.requests) * 100)
          : 0,
    }));

    const methodData = Object.values(methods);

    const responseTimeData = Object.entries(responseTimes).map(
      ([range, count]) => ({
        range,
        count,
      })
    );

    return {
      timeSeriesData,
      statusCodeData,
      endpointData,
      methodData,
      responseTimeData,
    };
  };

  // Generate anomaly data based on actual logs
  const detectAnomalies = () => {
    if (!logs || logs.length === 0) {
      return [];
    }

    const anomalies = [];
    const processed = processData();

    // Detect response time spikes
    const avgResponseTimes = processed.timeSeriesData.map(
      (item) => item.avgResponseTime
    );
    const avgResponseTime =
      avgResponseTimes.reduce((sum, time) => sum + time, 0) /
      avgResponseTimes.length;
    const highResponseTimeThreshold = avgResponseTime * 2;

    processed.timeSeriesData.forEach((item) => {
      if (item.avgResponseTime > highResponseTimeThreshold) {
        anomalies.push({
          id: `anomaly-resp-${item.time}`,
          timestamp: item.time,
          type: "Response time spike",
          severity: "High",
          message: `Unusually high response time (${item.avgResponseTime}ms) detected at ${item.time}`,
        });
      }
    });

    // Detect high error rates
    processed.endpointData.forEach((endpoint) => {
      if (endpoint.errorRate > 30) {
        anomalies.push({
          id: `anomaly-err-${endpoint.endpoint}`,
          timestamp: new Date().toLocaleTimeString(),
          type: "High error rate",
          severity: endpoint.errorRate > 50 ? "High" : "Medium",
          message: `High error rate (${endpoint.errorRate}%) detected on ${endpoint.endpoint}`,
        });
      }
    });

    // Return the top 3 anomalies
    return anomalies.slice(0, 3);
  };

  const data = processData();
  const anomalies = detectAnomalies();

  // Get total success and error counts
  const totalRequests = logs.length;
  const successCount = logs.filter((log) => log.status_code < 400).length;
  const errorCount = logs.filter((log) => log.status_code >= 400).length;
  const successRate =
    totalRequests > 0 ? ((successCount / totalRequests) * 100).toFixed(1) : 0;
  const avgResponseTime =
    totalRequests > 0
      ? Math.round(
          logs.reduce((sum, log) => sum + (log.response_time_ms || 0), 0) /
            totalRequests
        )
      : 0;

  return (
    <div className="bg-gray-50 min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">
              API Monitoring Dashboard
            </h1>
            <p className="text-gray-500">
              Last refreshed: {lastRefreshed.toLocaleTimeString()}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Auto-refresh:</span>
              <select
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
                className="border rounded p-1 text-sm"
              >
                <option value="5">5 seconds</option>
                <option value="10">10 seconds</option>
                <option value="30">30 seconds</option>
                <option value="60">1 minute</option>
              </select>
            </div>
            <button
              onClick={handleManualRefresh}
              className="flex items-center gap-1 bg-primary text-white px-3 py-1 rounded"
            >
              <RefreshCw size={16} />
              <span>Refresh</span>
            </button>
          </div>
        </header>

        {loading ? (
          <div className="text-center py-10">
            <p className="text-gray-600">Loading data...</p>
          </div>
        ) : error ? (
          <div className="bg-errorLight p-4 rounded-lg mb-6">
            <p className="text-error">{error}</p>
            <p className="text-gray-600 mt-2">
              Please check that your API log endpoint is accessible and
              returning data.
            </p>
          </div>
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <div className="bg-white rounded-lg shadow p-4 border-l-4 border-primary">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-gray-500 text-sm">Total Requests</p>
                    <h2 className="text-2xl font-bold">{totalRequests}</h2>
                  </div>
                  <Activity className="text-primary" />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-4 border-l-4 border-success">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-gray-500 text-sm">Success Rate</p>
                    <h2 className="text-2xl font-bold">{successRate}%</h2>
                  </div>
                  <Clock className="text-success" />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-4 border-l-4 border-warning">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-gray-500 text-sm">Avg Response Time</p>
                    <h2 className="text-2xl font-bold">{avgResponseTime} ms</h2>
                  </div>
                  <Clock className="text-warning" />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-4 border-l-4 border-error">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-gray-500 text-sm">Error Count</p>
                    <h2 className="text-2xl font-bold">{errorCount}</h2>
                  </div>
                  <AlertTriangle className="text-error" />
                </div>
              </div>
            </div>

            {data.timeSeriesData.length > 0 ? (
              <>
                {/* Traffic Overview Chart */}
                <div className="bg-white rounded-lg shadow p-4 mb-6">
                  <h2 className="text-lg font-bold mb-4">
                    API Traffic Overview
                  </h2>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={data.timeSeriesData}
                        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="time" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="requests"
                          stroke={COLORS.primary}
                          name="Requests"
                          strokeWidth={2}
                        />
                        <Line
                          type="monotone"
                          dataKey="avgResponseTime"
                          stroke={COLORS.warning}
                          name="Avg Response Time (ms)"
                          strokeWidth={2}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Status Codes and Endpoint Performance */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                  {/* Status Code Distribution */}
                  <div className="bg-white rounded-lg shadow p-4">
                    <h2 className="text-lg font-bold mb-4">
                      Status Code Distribution
                    </h2>
                    <div className="h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={data.statusCodeData}
                          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="code" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Bar dataKey="count" name="Count">
                            {data.statusCodeData.map((entry, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={getStatusCodeColor(entry.code)}
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Endpoint Performance */}
                  <div className="bg-white rounded-lg shadow p-4">
                    <h2 className="text-lg font-bold mb-4">
                      Endpoint Performance
                    </h2>
                    <div className="h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={data.endpointData}
                          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                          layout="vertical"
                        >
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis type="number" />
                          <YAxis
                            dataKey="endpoint"
                            type="category"
                            width={80}
                          />
                          <Tooltip />
                          <Legend />
                          <Bar
                            dataKey="avgResponseTime"
                            name="Avg Response Time (ms)"
                            fill={COLORS.warning}
                          />
                          <Bar
                            dataKey="errorRate"
                            name="Error Rate (%)"
                            fill={COLORS.error}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                {/* Anomaly Detection and Recent Requests */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                  {/* Anomaly Detection */}
                  <div className="bg-white rounded-lg shadow p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h2 className="text-lg font-bold">Anomaly Detection</h2>
                      <span className="bg-errorLight text-error text-xs px-2 py-1 rounded-full">
                        {anomalies.length} anomalies detected
                      </span>
                    </div>
                    {anomalies.length > 0 ? (
                      <div className="space-y-3">
                        {anomalies.map((anomaly) => (
                          <div
                            key={anomaly.id}
                            className="border-l-4 p-3 bg-gray-50 rounded"
                            style={{
                              borderColor:
                                anomaly.severity === "High"
                                  ? COLORS.error
                                  : anomaly.severity === "Medium"
                                  ? COLORS.warning
                                  : COLORS.info,
                            }}
                          >
                            <div className="flex justify-between">
                              <span className="font-semibold">
                                {anomaly.type}
                              </span>
                              <span
                                className="text-xs px-2 py-0.5 rounded-full"
                                style={{
                                  backgroundColor:
                                    anomaly.severity === "High"
                                      ? `${COLORS.error}20`
                                      : anomaly.severity === "Medium"
                                      ? `${COLORS.warning}20`
                                      : `${COLORS.info}20`,
                                  color:
                                    anomaly.severity === "High"
                                      ? COLORS.error
                                      : anomaly.severity === "Medium"
                                      ? COLORS.warning
                                      : COLORS.info,
                                }}
                              >
                                {anomaly.severity}
                              </span>
                            </div>
                            <p className="text-sm text-gray-600 mt-1">
                              {anomaly.message}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                              {anomaly.timestamp}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-center text-gray-500 py-8">
                        No anomalies detected
                      </p>
                    )}
                  </div>

                  {/* Recent Requests */}
                  <div className="col-span-4 p-4 bg-gray-50 rounded-xl shadow-lg overflow-auto max-h-96">
                    <h2 className="text-xl font-bold mb-2 text-gray-800">
                      Recent API Logs
                    </h2>
                    <table className="w-full table-auto border-collapse text-gray-800">
                      <thead>
                        <tr className="bg-gray-700 text-gray-200">
                          <th className="p-2">Timestamp</th>
                          <th className="p-2">Method</th>
                          <th className="p-2">Endpoint</th>
                          <th className="p-2">Status</th>
                          <th className="p-2">Response Time (ms)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {logs.map((log, index) => (
                          <tr key={index} className="border-t border-gray-600">
                            <td className="p-2">{log.timestamp}</td>
                            <td className="p-2">{log.method}</td>
                            <td className="p-2">{log.url}</td>
                            <td
                              className={`p-2 ${
                                log.status_code >= 200 && log.status_code < 300
                                  ? "text-green-400"
                                  : "text-red-400"
                              }`}
                            >
                              {log.status_code}
                            </td>
                            <td className="p-2">{log.response_time_ms}</td>
                          </tr>
                        ))}
                        <tr ref={logsEndRef} />
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Throughput Analysis */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
                  {/* Success vs Error Rate */}
                  <div className="bg-white rounded-lg shadow p-4">
                    <h2 className="text-lg font-bold mb-4">
                      Success vs Error Rate
                    </h2>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={[
                              { name: "Success", value: successCount },
                              { name: "Error", value: errorCount },
                            ]}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            outerRadius={80}
                            fill="#8884d8"
                            dataKey="value"
                            label={({ name, percent }) =>
                              `${name}: ${(percent * 100).toFixed(1)}%`
                            }
                          >
                            <Cell fill={COLORS.success} />
                            <Cell fill={COLORS.error} />
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* HTTP Methods Distribution */}
                  <div className="bg-white rounded-lg shadow p-4">
                    <h2 className="text-lg font-bold mb-4">HTTP Methods</h2>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={data.methodData}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            outerRadius={80}
                            fill="#8884d8"
                            dataKey="count"
                            nameKey="name"
                            label={({ name, percent }) =>
                              `${name}: ${(percent * 100).toFixed(1)}%`
                            }
                          >
                            {data.methodData.map((entry, index) => {
                              const colors = [
                                COLORS.info,
                                COLORS.success,
                                COLORS.warning,
                                COLORS.error,
                                COLORS.primary,
                              ];
                              return (
                                <Cell
                                  key={`cell-${index}`}
                                  fill={colors[index % colors.length]}
                                />
                              );
                            })}
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Response Time Distribution */}
                  <div className="bg-white rounded-lg shadow p-4">
                    <h2 className="text-lg font-bold mb-4">
                      Response Time Distribution
                    </h2>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={data.responseTimeData}
                          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="range" />
                          <YAxis />
                          <Tooltip />
                          <Bar
                            dataKey="count"
                            name="Requests"
                            fill={COLORS.primary}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="bg-white rounded-lg shadow p-10 text-center mb-6">
                <h2 className="text-lg font-semibold mb-2">
                  No log data available
                </h2>
                <p className="text-gray-600">
                  The dashboard is connected to your /log endpoint, but no data
                  was found. Wait for new API calls or check your endpoint.
                </p>
              </div>
            )}
          </>
        )}

        {/* Footer */}
        <footer className="text-center text-gray-500 text-sm py-4">
          API Monitoring Dashboard • Last updated:{" "}
          {lastRefreshed.toLocaleString()}
        </footer>
      </div>
    </div>
  );
};

export default Dashboard;
