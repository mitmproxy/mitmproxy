import { combineReducers } from 'redux'
import eventLog from './eventLog'
import flows from './flows'
import settings from './settings'
import ui from './ui/index'

export default combineReducers({
    eventLog,
    flows,
    settings,
    ui,
})
