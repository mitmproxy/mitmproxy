const TOGGLE_FILTER = 'TOGGLE_EVENTLOG_FILTER'
const TOGGLE_VISIBILITY = 'TOGGLE_EVENTLOG_VISIBILITY'


const defaultState = {
    visible: false,
    filter: {
        "debug": false,
        "info": true,
        "web": true
    }
}
export default function reducer(state = defaultState, action) {
    switch (action.type) {
        case TOGGLE_FILTER:
            return {
                ...state,
                filter: {
                    ...state.filter,
                    [action.filter]: !state.filter[action.filter]
                }
            }
        case TOGGLE_VISIBILITY:
            return {
                ...state,
                visible: !state.visible
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