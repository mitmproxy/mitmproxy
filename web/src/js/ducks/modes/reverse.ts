import { createModeUpdateThunk, addSetter } from "./utils";
import { ReverseProxyProtocols } from "../../backends/consts";
import { BackendState, STATE_RECEIVE, STATE_UPDATE } from "../backendState";
import { shallowEqual } from "react-redux";
import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import {
    defaultReverseState,
    getSpec,
    parseRaw,
    ReverseState,
} from "../../modes/reverse";
import { parseSpec } from "../../modes";

export const setActive = createModeUpdateThunk<boolean>(
    "modes/reverse/setActive",
);
export const setListenHost = createModeUpdateThunk<string | undefined>(
    "modes/reverse/setListenHost",
);
export const setListenPort = createModeUpdateThunk<number | undefined>(
    "modes/reverse/setListenPort",
);
export const setProtocol = createModeUpdateThunk<ReverseProxyProtocols>(
    "modes/reverse/setProtocol",
);
export const setDestination = createModeUpdateThunk<string>(
    "modes/reverse/setDestination",
);

export const initialState: ReverseState[] = [defaultReverseState()];

export const reverseSlice = createSlice({
    name: "modes/reverse",
    initialState,
    reducers: {
        addServer: (state) => {
            state.push(defaultReverseState());
        },
        removeServer: (state, action: PayloadAction<ReverseState>) => {
            const index = state.findIndex(
                (m) => m.ui_id === action.payload.ui_id,
            );
            if (index !== -1) {
                if (state[index].active)
                    console.error(
                        "servers should be deactivated before removal",
                    );
                state.splice(index, 1);
            }
        },
    },
    extraReducers: (builder) => {
        addSetter(builder, "active", setActive);
        addSetter(builder, "listen_host", setListenHost);
        addSetter(builder, "listen_port", setListenPort);
        addSetter(builder, "protocol", setProtocol);
        addSetter(builder, "destination", setDestination);

        builder.addCase(STATE_RECEIVE, updateState);
        builder.addCase(STATE_UPDATE, updateState);
        function updateState(
            state: ReverseState[],
            action: PayloadAction<Partial<BackendState>>,
        ) {
            if (action.payload.servers) {
                // action.data.servers does not include servers that are currently inactive,
                // but we want to keep them in the UI. So we need to merge UI state with what we got from the server.

                const activeServers = Object.fromEntries(
                    Object.entries(action.payload.servers)
                        .filter(([_, info]) => info.type === "reverse")
                        .map(([spec, _]) => [spec, parseSpec(spec)]),
                );

                const nextState: ReverseState[] = [];

                // keep current UI state as is, but correct `active` bit.
                for (const server of state) {
                    const spec = getSpec(server);
                    const active = spec in activeServers;
                    delete activeServers[spec];
                    nextState.push({
                        ...server,
                        active,
                    });
                }

                // add all new specs
                for (const x of Object.values(activeServers)) {
                    nextState.push(parseRaw(x));
                }

                // remove default config if still present.
                if (
                    nextState.length > 1 &&
                    shallowEqual(
                        {
                            ...nextState[0],
                            ui_id: undefined,
                        } as ReverseState,
                        {
                            ...defaultReverseState(),
                            ui_id: undefined,
                        } as ReverseState,
                    )
                ) {
                    nextState.shift();
                }

                return nextState;
            }
        }
    },
});
export const { addServer, removeServer } = reverseSlice.actions;
export default reverseSlice.reducer;
