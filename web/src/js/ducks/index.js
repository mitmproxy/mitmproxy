import {combineReducers} from 'redux'
import eventLog from './eventLog.js'
import websocket from './websocket.js'
import flows from './flows.js'

const rootReducer = combineReducers({
    eventLog,
    flows,
    websocket,
})

export default rootReducer