import { SELECT_FLOW } from './flows'
const SET_ACTIVE_MENU = 'SET_ACTIVE_MENU'


const defaultState = {
    active_menu: 'Start'
}
export default function reducer(state = defaultState, action) {
    switch (action.type) {
        case SET_ACTIVE_MENU:
            return {
                ...state,
                active_menu: action.active_menu
            }
        case SELECT_FLOW:
            let isNewSelection = (action.flowId && !action.currentSelection)
            let isSelectAction = action.flowId
            if (isNewSelection){
                let wasFlowSelected = state.active_menu == 'Flow'
                return{
                    ...state,
                    active_menu: isSelectAction ? 'Flow' : (wasFlowSelected ? 'Start' : state.active_menu)
                }
            }
            return state
        default:
            return state
    }
}

export function setActiveMenu(active_menu) {
    return {
        type: SET_ACTIVE_MENU,
        active_menu
    }
}

