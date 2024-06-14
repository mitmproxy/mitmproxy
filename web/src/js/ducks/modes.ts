import { combineReducers } from "redux";
import regularReducer from "./modes/regular";
import { fetchApi } from "../utils";

export interface ModeState {
    active: boolean;
    listen_port?: number;
    listen_host?: string;
}

export const updateMode = async (mode, active) => {
    try {
        const response = await fetchApi.put("/options", {
            ["mode"]: active ? [] : [mode],
        });
        if (response.status === 200) {
            return { success: true };
        } else {
            const errorText = await response.text();
            throw new Error(errorText);
        }
    } catch (error) {
        return { success: false, error: error.message };
    }
};

const modes = combineReducers({
    regular: regularReducer,
    //add new modes here
});

export default modes;
