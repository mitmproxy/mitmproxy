import { SELECT_FLOW } from './flows'
const SET_ACTIVE_MENU = 'SET_ACTIVE_MENU'


const defaultState = {
    activeMenu: 'Start',
}
export default function reducer(state = defaultState, action) {
    switch (action.type) {
        case SET_ACTIVE_MENU:
            return {
                ...state,
                activeMenu: action.activeMenu
            }
        case SELECT_FLOW:
            let isNewSelect = (action.flowId && !action.currentSelection)
            let isDeselect = (!action.flowId && action.currentSelection)
            if(isNewSelect) {
                return {
                    ...state,
                    activeMenu: "Flow"
                }
            }
            if(isDeselect && state.activeMenu === "Flow") {
                return {
                    ...state,
                    activeMenu: "Start"
                }
            }
            return state
        default:
            return state
    }
}

export function setActiveMenu(activeMenu) {
    return {
        type: SET_ACTIVE_MENU,
        activeMenu
    }
}

