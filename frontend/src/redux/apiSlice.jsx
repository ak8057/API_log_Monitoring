import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";

export const fetchLogs = createAsyncThunk("logs/fetchLogs", async () => {
  const response = await axios.get("http://127.0.0.1:8000/logs");
  return response.data;
});

const apiSlice = createSlice({
  name: "api",
  initialState: { logs: [], status: "idle" },
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(fetchLogs.fulfilled, (state, action) => {
      state.logs = action.payload;
    });
  },
});

export default apiSlice.reducer;
