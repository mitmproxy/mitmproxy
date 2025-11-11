import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type Version = "web" | "webnext";

export interface VersionState {
    value: Version;
}

const defaultState: VersionState = {
    value: "web",
};

export const createVersionSlice = (
    initialState: VersionState = defaultState,
) => {
    return createSlice({
        name: "ui/version",
        initialState,
        reducers: {
            setVersion(state, action: PayloadAction<Version>) {
                state.value = action.payload;
            },
        },
    });
};
