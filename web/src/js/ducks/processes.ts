import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { fetchApi } from "../utils";

export interface Process {
    is_visible: boolean;
    executable: string;
    is_system: boolean;
    display_name: string;
}

export interface Processes {
    currentProcesses: Process[];
    isLoading?: boolean;
    error?: string;
}

export const fetchProcesses = createAsyncThunk(
    "fetchProcesses",
    async (_, { rejectWithValue }) => {
        try {
            const response = await fetchApi("/processes");
            return response.json();
        } catch (error) {
            return rejectWithValue((error as Error).message);
        }
    },
);

export const initialState: Processes = {
    currentProcesses: [],
    isLoading: false,
};

export const processesSlice = createSlice({
    name: "processes",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        builder.addCase(fetchProcesses.pending, (state) => {
            state.isLoading = true;
            state.error = undefined;
        });
        builder.addCase(fetchProcesses.fulfilled, (state, action) => {
            state.isLoading = false;
            state.currentProcesses = action.payload as Process[];
        });
        builder.addCase(fetchProcesses.rejected, (state, action) => {
            state.isLoading = false;
            state.error = action.payload as string;
        });
    },
});

export default processesSlice.reducer;
