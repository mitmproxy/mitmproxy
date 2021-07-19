import * as flowsActions from "../flows"

export const SET_ACTIVE_MENU = 'UI_SET_ACTIVE_MENU'


const defaultState = {
    activeMenu: 'Start',
    isFlowSelected: false,
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {

        case SET_ACTIVE_MENU:
            return {
                ...state,
                activeMenu: action.activeMenu,
            }

        case flowsActions.SELECT:
            // First Select
            if (action.flowIds.length > 0 && !state.isFlowSelected) {
                return {
                    ...state,
                    activeMenu: 'Flow',
                    isFlowSelected: true,
                }
            }

            // Deselect
            if (action.flowIds.length === 0 && state.isFlowSelected) {
                let activeMenu = state.activeMenu
                if (activeMenu === 'Flow') {
                    activeMenu = 'Start'
                }
                return {
                    ...state,
                    activeMenu,
                    isFlowSelected: false,
                }
            }
            return state
        default:
            return state
    }
}

export function setActiveMenu(activeMenu) {
    return { type: SET_ACTIVE_MENU, activeMenu }
}
