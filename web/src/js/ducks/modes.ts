import { combineReducers } from "redux";
import regularReducer from "./modes/regular";
import localReducer from "./modes/local";
import wireguardReducer from "./modes/wireguard";
import reverseReducer from "./modes/reverse";
import transparentReducer from "./modes/transparent";
import socksReducer from "./modes/socks";
import upstreamReducer from "./modes/upstream";
import dnsReducer from "./modes/dns";

const modes = combineReducers({
    regular: regularReducer,
    local: localReducer,
    wireguard: wireguardReducer,
    reverse: reverseReducer,
    transparent: transparentReducer,
    socks: socksReducer,
    upstream: upstreamReducer,
    dns: dnsReducer,
    //add new modes here
});

export type ModesState = ReturnType<typeof modes>;

export default modes;
