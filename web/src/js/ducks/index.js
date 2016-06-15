import {combineReducers} from 'redux'
import eventLog from './eventLog'
import websocket from './websocket'
import flows from './flows'
import ui from './ui.js'

const rootReducer = combineReducers({
    eventLog,
    websocket,
    flows,
    ui
})

export default rootReducer
