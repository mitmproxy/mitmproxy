import { combineReducers } from "redux"
import eventLog from "./eventLog"
import flows from "./flows"
import settings from "./settings"
import ui from "./ui/index"
import connection from "./connection"

export default combineReducers({
    eventLog,
    flows,
    settings,
    connection,
    ui,
})
