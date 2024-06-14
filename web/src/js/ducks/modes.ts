import { combineReducers } from "redux";
import regularReducer from "./modes/regular";
import { fetchApi } from "../utils";

export interface ModeState {
    active: boolean;
    listen_port?: number;
    listen_host?: string;
    error?: string;
}

export const updateMode = () => {
    return async (_, getState) => {
        try {
            const state = getState().modes;

            const activeModes: string[] = [];

            Object.keys(state).forEach((key) => {
                const modeState = state[key];
                if (modeState.active) {
                    let mode = key;
                    if (modeState.listen_host) {
                        mode += `@${modeState.listen_host}`;
                    }
                    if (modeState.listen_port) {
                        mode += `:${modeState.listen_port}`;
                    }
                    activeModes.push(mode);
                }
            });
            console.log(activeModes);
            const response = await fetchApi.put("/options", {
                mode: activeModes,
            });
            if (response.status === 200) {
                return { success: true };
            } else {
                const errorText = await response.text();
                return { success: false, error: errorText };
            }
        } catch (error) {
            return { success: false, error: error.message };
        }
    };
};

const modes = combineReducers({
    regular: regularReducer,
    //add new modes here
});

export default modes;
