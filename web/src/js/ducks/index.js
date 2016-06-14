import {combineReducers} from 'redux'
import eventLog from './eventLog'
import websocket from './websocket'
import flows from './flows'
import view from './view'

const rootReducer = combineReducers({
    eventLog,
    websocket,
    flows,
    view
})

export default rootReducer
