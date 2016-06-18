import { connect as wsConnect, disconnect as wsDisconnect } from './websocket'

export const INIT = 'APP_INIT'

const defaultState = {}

export function reduce(state = defaultState, action) {
    switch (action.type) {

        default:
            return state
    }
}

export function init() {
    return dispatch => {
        dispatch(wsConnect())
        dispatch({ type: INIT })
    }
}

export function destruct() {
    return dispatch => {
        dispatch(wsDisconnect())
        dispatch({ type: DESTRUCT })
    }
}
