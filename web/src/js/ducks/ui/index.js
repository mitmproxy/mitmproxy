import { combineReducers } from 'redux'
import flow from './flow'
import header from './header'
import focus from './focus'
import prompt from './prompt'

export default combineReducers({
    flow,
    header,
    focus,
    prompt,
})
