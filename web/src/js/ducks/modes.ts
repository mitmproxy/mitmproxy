import { combineReducers } from "redux";
import regularReducer from "./modes/regular";
import localReducer from "./modes/local";
import wireguardReducer from "./modes/wireguard";

const modes = combineReducers({
    regular: regularReducer,
    local: localReducer,
    wireguard: wireguardReducer,
    //add new modes here
});

export type ModesState = ReturnType<typeof modes>;

export default modes;
