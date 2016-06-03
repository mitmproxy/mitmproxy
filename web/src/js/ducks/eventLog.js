import getList, {ADD} from "./list"
const TOGGLE_FILTER = 'TOGGLE_EVENTLOG_FILTER'
const TOGGLE_VISIBILITY = 'TOGGLE_EVENTLOG_VISIBILITY'
const UPDATE_LIST = "UPDATE_EVENTLOG"


const defaultState = {
    visible: false,
    filter: {
        "debug": false,
        "info": true,
        "web": true
    },
    events: getList(),
    filteredEvents: [],
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {
        case TOGGLE_FILTER:
            const filter = {
                ...state.filter,
                [action.filter]: !state.filter[action.filter]
            }
            return {
                ...state,
                filter,
                filteredEvents: state.events.list.filter(x => filter[x.level])
            }
        case TOGGLE_VISIBILITY:
            return {
                ...state,
                visible: !state.visible
            }
        case UPDATE_LIST:
            const events = getList(state.events, action)
            return {
                ...state,
                events,
                filteredEvents: events.list.filter(x => state.filter[x.level])
            }
        default:
            return state
    }
}


export function toggleEventLogFilter(filter) {
    return {type: TOGGLE_FILTER, filter}
}
export function toggleEventLogVisibility() {
    return {type: TOGGLE_VISIBILITY}
}
let id = 0;
export function addLogEntry(message, level = "web") {
    return {
        type: UPDATE_LIST,
        cmd: ADD,
        data: {message, level, id: `log-${id++}`}
    }
}