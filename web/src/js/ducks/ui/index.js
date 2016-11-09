import { combineReducers } from 'redux'
import flow from './flow'
import header from './header'

// TODO: Just move ducks/ui/* into ducks/?
export default combineReducers({
    flow,
    header,
})
