import {
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { addSetter, createModeUpdateThunk, updateState } from "./utils";
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { LocalState, parseRaw, Process } from "../../modes/local";
import { fetchApi } from "../../utils";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/local/setActive",
);
export const setSelectedApplications = createModeUpdateThunk<
    string | undefined
>("modes/local/setSelectedApplications");

export const fetchProcesses = createAsyncThunk(
    "modes/local/fetchProcesses",
    async (_, { rejectWithValue }) => {
        try {
            const response = await fetchApi("/processes");
            return response.json();
        } catch (error) {
            return rejectWithValue(error.message);
        }
    },
);

export const initialState: LocalState[] = [
    {
        active: false,
        isLoading: false,
        currentProcesses: [],
        selectedApplications: "",
        ui_id: Math.random(),
    },
];

export const localSlice = createSlice({
    name: "modes/local",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "selectedApplications", setSelectedApplications);
        builder.addCase(RECEIVE_STATE, updateState("local", parseRaw));
        builder.addCase(UPDATE_STATE, updateState("local", parseRaw));
        builder.addCase(fetchProcesses.pending, (state) => {
            state[0].isLoading = true;
            state[0].error = undefined;
        });
        builder.addCase(fetchProcesses.fulfilled, (state, action) => {
            state[0].isLoading = false;
            state[0].currentProcesses = action.payload as Process[];
        });
        builder.addCase(fetchProcesses.rejected, (state, action) => {
            state[0].isLoading = false;
            state[0].error = action.payload as string;
        });
    },
});

export default localSlice.reducer;
