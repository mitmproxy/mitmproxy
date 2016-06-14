import { SELECT_FLOW } from './flows'
const ACTIVE_MENU = 'ACTIVE_MENU'


const defaultState = {
    active_menu: 'Start'
}
export default function reducer(state = defaultState, action) {
    switch (action.type) {
        case ACTIVE_MENU:
            return {
                ...state,
                active_menu: action.active_menu
            }
        case SELECT_FLOW:
            return{
                ...state,
                active_menu: action.flowId ? 'Flow' : 'Start'
            }
        default:
            return state
    }
}

export function setActiveMenu(active_menu) {
    return {
        type: ACTIVE_MENU,
        active_menu
    }
}

