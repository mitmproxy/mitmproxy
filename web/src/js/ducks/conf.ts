/**
 * Conf houses properties about the current mitmproxy instance that are not options,
 * e.g. the list of available content views or the current version.
 */
import {Reducer} from "redux";

interface ConfState {
    static: boolean
    version: string
    contentViews: string[]
}

// @ts-ignore
export const defaultState: ConfState = window.MITMWEB_CONF || {
    static: false,
    version: "1.2.3",
    contentViews: ["Auto", "Raw"],
};

const reducer: Reducer<ConfState> = (state = defaultState, action): ConfState => {
    return state
}
export default reducer
