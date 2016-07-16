import {SELECT} from "./views/main"
export const SET_ACTIVE_MENU = 'SET_ACTIVE_MENU';


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
        case SELECT:
            let isNewSelect = (action.id && !action.currentSelection)
            let isDeselect = (!action.id && action.currentSelection)
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

