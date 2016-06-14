const ACTIVE_MENU = 'ACTIVE_MENU'
const DEFAULT_MENU = 'DEFAULT_MENU'
const FLOW_MENU = 'FLOW_MENU'


const defaultState = {
    active_menu: 'Start',
}
export default function reducer(state = defaultState, action) {
    switch (action.type) {
        case ACTIVE_MENU:
            return {
               ...state,
                active_menu: action.active_menu
            }
        case DEFAULT_MENU:
            return {
                ...state,
                active_menu: defaultState.active_menu
            }
        case FLOW_MENU:
            return {
                ... state,
                active_menu: "Flow"
            }


        default:
            return state
    }
}

export function setDefaultMenu(active_menu) {
    return {
        type: DEFAULT_MENU,
    }
}
export function setFlowMenu() {
    return {
        type: FLOW_MENU,
    }
}

export function setActiveMenu(active_menu) {
    return {
        type: ACTIVE_MENU,
        active_menu
    }
}

