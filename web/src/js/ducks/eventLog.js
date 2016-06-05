import makeList from "./utils/list"
import {updateViewFilter, updateViewList} from "./utils/view"

const TOGGLE_FILTER = 'TOGGLE_EVENTLOG_FILTER'
const TOGGLE_VISIBILITY = 'TOGGLE_EVENTLOG_VISIBILITY'
export const UPDATE_LOG = "UPDATE_EVENTLOG"

const {
    reduceList,
    updateList,
    fetchList,
    addItem,
} = makeList(UPDATE_LOG, "/events")


const defaultState = {
    visible: false,
    filter: {
        "debug": false,
        "info": true,
        "web": true
    },
    events: reduceList(),
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
                filteredEvents: updateViewFilter(
                    state.events,
                    x => filter[x.level]
                )
            }
        case TOGGLE_VISIBILITY:
            return {
                ...state,
                visible: !state.visible
            }
        case UPDATE_LOG:
            const events = reduceList(state.events, action)
            return {
                ...state,
                events,
                filteredEvents: updateViewList(
                    state.filteredEvents,
                    state.events,
                    events,
                    action,
                    x => state.filter[x.level]
                )
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
let id = 0
export function addLogEntry(message, level = "web") {
    return addItem({
        message,
        level,
        id: `log-${id++}`
    })
}
export {updateList as updateLogEntries, fetchList as fetchLogEntries}