import {
    BackendState,
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { addSetter, getModesOfType, createModeUpdateThunk } from "./utils";
import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { RegularState } from "../../modes/regular";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/regular/setActive",
);
export const setListenHost = createModeUpdateThunk<string | undefined>(
    "modes/regular/setListenHost",
);
export const setListenPort = createModeUpdateThunk<number | undefined>(
    "modes/regular/setListenPort",
);

export const initialState: RegularState[] = [
    {
        active: true,
        ui_id: Math.random(),
    },
];

export const regularSlice = createSlice({
    name: "modes/regular",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "listen_host", setListenHost);
        addSetter(builder, "listen_port", setListenPort);

        builder.addCase(RECEIVE_STATE, updateState);
        builder.addCase(UPDATE_STATE, updateState);
        function updateState(
            state: RegularState[],
            action: PayloadAction<Partial<BackendState>>,
        ) {
            if (action.payload.servers) {
                const activeRegularModes = getModesOfType(
                    "regular",
                    action.payload.servers,
                );
                if (activeRegularModes.length > 0) {
                    return activeRegularModes.map(
                        (m) =>
                            ({
                                ui_id: Math.random(),
                                active: true,
                                listen_host: m.listen_host,
                                listen_port: m.listen_port,
                            }) as RegularState,
                    );
                } else {
                    for (const mode of state) {
                        mode.active = false;
                    }
                }
            }
        }
    },
});

export default regularSlice.reducer;
