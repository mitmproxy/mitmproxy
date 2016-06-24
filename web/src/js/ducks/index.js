import { combineReducers } from 'redux'
import eventLog from './eventLog'
import websocket from './websocket'
import flows from './flows'
import settings from './settings'
import ui from './ui'
import msgQueue from './msgQueue'

export default combineReducers({
    eventLog,
    websocket,
    flows,
    settings,
    ui,
    msgQueue,
})
