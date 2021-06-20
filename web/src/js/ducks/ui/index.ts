import { combineReducers } from 'redux'
import flow from './flow'
import header from './header'
import modal from './modal'
import optionsEditor from './optionsEditor'

// TODO: Just move ducks/ui/* into ducks/?
export default combineReducers({
    flow,
    header,
    modal,
    optionsEditor,
})
