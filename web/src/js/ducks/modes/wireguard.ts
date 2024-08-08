import { WireguardState } from "../../modes/wireguard";
import {
    BackendState,
    RECEIVE as RECEIVE_STATE,
    UPDATE as UPDATE_STATE,
} from "../backendState";
import { addSetter, getModesOfType, createModeUpdateThunk } from "./utils";
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/wireguard/setActive",
);
export const setListenHost = createModeUpdateThunk<string | undefined>(
    "modes/wireguard/setListenHost",
);
export const setListenPort = createModeUpdateThunk<number | undefined>(
    "modes/wireguard/setListenPort",
);
export const setFilePath = createModeUpdateThunk<string | undefined>(
    "modes/wireguard/setFilePath",
);

export const initialState: WireguardState[] = [
    {
        active: false,
        file_path: "",
        listen_port: 51820,
        ui_id: Math.random(),
    },
];

export const wireguardSlice = createSlice({
    name: "modes/wireguard",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "listen_host", setListenHost);
        addSetter(builder, "listen_port", setListenPort);
        addSetter(builder, "file_path", setFilePath);

        builder.addCase(RECEIVE_STATE, updateState);
        builder.addCase(UPDATE_STATE, updateState);

        function updateState(
            state: WireguardState[],
            action: PayloadAction<Partial<BackendState>>,
        ) {
            if (action.payload.servers) {
                const activeWireguardModes = getModesOfType(
                    "wireguard",
                    action.payload.servers,
                );
                if (activeWireguardModes.length > 0) {
                    return activeWireguardModes.map(
                        (m) =>
                            ({
                                ui_id: Math.random(),
                                active: true,
                                listen_host: m.listen_host,
                                listen_port: m.listen_port,
                                file_path: m.data,
                            }) as WireguardState,
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

export default wireguardSlice.reducer;
