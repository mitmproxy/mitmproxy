import { combineReducers, applyMiddleware, createStore as createReduxStore } from 'redux'
import thunk from 'redux-thunk'

export function createStore(parts) {
    return createReduxStore(
        combineReducers(parts),
        applyMiddleware(...[thunk])
    )
}

export function TFlow(intercepted=false, marked=false, modified=false) {
    return {
        intercepted : intercepted,
        marked : marked,
        modified: modified,
        id: "foo",
        request: {
            scheme: 'http',
            is_replay: true,
            method: 'GET',
            contentLength: 100
        },
        response: {
            status_code: 200,
            headers: [["Content-Type", 'text/html']],
            timestamp_end: 200
        },
        error: {
            msg: ''
        },
        server_conn: {
            timestamp_start: 100
        },
        type: 'http'
    }
}
