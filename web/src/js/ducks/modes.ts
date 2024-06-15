import { combineReducers } from "redux";
import regularReducer, {
    getMode as getRegularModeConfig,
} from "./modes/regular";
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
            const modes = getState().modes;

            const activeModes: string[] = [getRegularModeConfig(modes)].filter(
                (mode) => mode !== ""
            );
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
