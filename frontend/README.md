# API Monitoring Dashboard

This folder contains the React/Vite dashboard for the API log monitoring demo. It reads live data from `http://127.0.0.1:8000/logs` and renders request volume, error rate, response time, anomaly summaries, and recent log rows.

## Structure

- `src/main.jsx` mounts the app.
- `src/App.jsx` composes the navbar and dashboard.
- `src/Pages/Dashboard.jsx` fetches the log stream and renders the charts and tables.
- `src/components/Navbar.jsx` contains the top banner.
- `src/components/Chart.jsx` is an auxiliary chart component.
- `src/redux/apiSlice.jsx` is Redux Toolkit scaffolding and is not wired into the current dashboard flow.

## Run

```bash
npm install
npm run dev
```

The dashboard expects the FastAPI backend to be running on `127.0.0.1:8000`.

## Notes

- The current implementation uses direct `fetch` calls rather than Redux for the main dashboard data path.
- The design is intentionally lightweight and pairs with the top-level README sections for architecture, Docker, and Kibana.
