import {combineReducers} from 'redux'
import eventLog from './eventLog.js'
import websocket from './websocket.js'

const rootReducer = combineReducers({
    eventLog,
    websocket,
})

export default rootReducer