import {
    BackendState,
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import {
    addSetter,
    getModesOfType,
    isActiveMode,
    includeListenAddress,
    ModeState,
    updateModes,
} from "./utils";
import { createSlice } from "@reduxjs/toolkit";
import { createAppAsyncThunk } from "../hooks";
import { ModesState } from "../modes";

interface RegularState extends ModeState {}

export const initialState: RegularState = {
    active: true,
};

export const getSpecs = ({ regular }: ModesState): string[] => {
    if (!isActiveMode(regular)) {
        return [];
    }
    return [includeListenAddress("regular", regular)];
};

export const setActive = createAppAsyncThunk<void, boolean>(
    "modes/regular/setActive",
    updateModes,
);
export const setListenHost = createAppAsyncThunk<void, string | undefined>(
    "modes/regular/setListenHost",
    updateModes,
);
export const setListenPort = createAppAsyncThunk<void, number | undefined>(
    "modes/regular/setListenPort",
    updateModes,
);

export const regularSlice = createSlice({
    name: "modes/regular",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "listen_host", setListenHost);
        addSetter(builder, "listen_port", setListenPort);

        builder.addCase(UPDATE_STATE, updateState);
        builder.addCase(RECEIVE_STATE, updateState);
        function updateState(state: RegularState, action: any) {
            if (action.data && action.data.servers) {
                const currentModeConfig = getModesOfType(
                    "regular",
                    action.data.servers,
                )[0];
                state.active = currentModeConfig !== undefined;
                if (state.active) {
                    state.listen_host = currentModeConfig.listen_host;
                    state.listen_port = currentModeConfig.listen_port as number;
                    state.error = undefined;
                }
            }
        }
    },
});

export default regularSlice.reducer;
