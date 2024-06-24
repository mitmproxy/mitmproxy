import { combineReducers } from "redux";
import regularReducer from "./modes/regular";
import localReducer from "./modes/local";

const modes = combineReducers({
    regular: regularReducer,
    local: localReducer,
    //add new modes here
});

export default modes;
