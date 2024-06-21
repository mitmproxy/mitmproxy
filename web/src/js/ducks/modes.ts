import { combineReducers } from "redux";
import regularReducer, {
    getMode as getRegularModeConfig,
} from "./modes/regular";
import { fetchApi } from "../utils";
import localReducer, { getMode as getLocalModeConfig } from "./modes/local";

const modes = combineReducers({
    regular: regularReducer,
    local: localReducer,
    //add new modes here
});

export default modes;
