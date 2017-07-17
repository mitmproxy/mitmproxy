import { combineReducers } from 'redux'
import flow from './flow'
import header from './header'
import modal from './modal'
import option from './option'

// TODO: Just move ducks/ui/* into ducks/?
export default combineReducers({
    flow,
    header,
    modal,
    option,
})
