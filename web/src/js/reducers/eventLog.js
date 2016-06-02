import {combineReducers} from 'redux'
import {TOGGLE_EVENTLOG_FILTER} from "../reduxActions"

const defaultVisibility = {
    "debug": false,
    "info": true,
    "web": true
};

const visibilityFilter = (state = defaultVisibility, action) => {
    switch (action.type) {
        case TOGGLE_EVENTLOG_FILTER:
            return Object.assign({}, state, {
                [action.filter]: !state[action.filter]
            });
        default:
            return state;
    }
};

const entries = (state = [], action) => {
    return state;
};

const eventLog = combineReducers({
    visibilityFilter,
    entries
});

export default eventLog
