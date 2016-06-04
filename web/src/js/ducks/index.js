import {combineReducers} from 'redux'
import eventLog from './eventLog'
import websocket from './websocket'
import flows from './flows'

const rootReducer = combineReducers({
    eventLog,
    websocket,
    flows,
})

export default rootReducer