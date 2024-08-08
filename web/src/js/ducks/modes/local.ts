import {
    BackendState,
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { addSetter, getModesOfType, createModeUpdateThunk } from "./utils";
import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { LocalState } from "../../modes/local";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/local/setActive",
);
export const setApplications = createModeUpdateThunk<string | undefined>(
    "modes/local/setApplications",
);

export const initialState: LocalState[] = [
    {
        active: false,
        applications: "",
        ui_id: Math.random(),
    },
];

export const localSlice = createSlice({
    name: "modes/local",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "applications", setApplications);

        builder.addCase(RECEIVE_STATE, updateState);
        builder.addCase(UPDATE_STATE, updateState);
        function updateState(
            state: LocalState[],
            action: PayloadAction<Partial<BackendState>>,
        ) {
            if (action.payload.servers) {
                const activeLocalModes = getModesOfType(
                    "local",
                    action.payload.servers,
                );
                if (activeLocalModes.length > 0) {
                    return activeLocalModes.map(
                        (m) =>
                            ({
                                ui_id: Math.random(),
                                active: true,
                                applications: m.data,
                            }) as LocalState,
                    );
                } else {
                    for (const mode of state) {
                        mode.active = false;
                    }
                }
            }
            return state;
        }
    },
});

export default localSlice.reducer;
