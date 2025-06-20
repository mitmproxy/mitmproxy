import { combineReducers } from "redux";
import flow from "./flow";
import modal from "./modal";
import optionsEditor from "./optionsEditor";
import tabs from "./tabs";
import filter from "./filter";

const initialPreferencesState = {
    timezoneDisplay: "utc" as "utc" | "local",
};

function preferences(state = initialPreferencesState, action: any) {
    switch (action.type) {
        case "SET_TIMEZONE_DISPLAY":
            return { ...state, timezoneDisplay: action.value };
        default:
            return state;
    }
}

export function setTimezoneDisplay(value: "utc" | "local") {
    return { type: "SET_TIMEZONE_DISPLAY", value };
}

export const selectTimezoneDisplay = (state: any) =>
    state.ui.preferences.timezoneDisplay;

export default combineReducers({
    flow,
    modal,
    optionsEditor,
    tabs,
    filter,
    preferences,
});
