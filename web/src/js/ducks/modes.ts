import { combineReducers } from "redux";
import regularReducer from "./modes/regular";
import localReducer from "./modes/local";
import wireguardReducer from "./modes/wireguard";
import reverseReducer from "./modes/reverse";

const modes = combineReducers({
    regular: regularReducer,
    local: localReducer,
    wireguard: wireguardReducer,
    reverse: reverseReducer,
    //add new modes here
});

export type ModesState = ReturnType<typeof modes>;

export default modes;
