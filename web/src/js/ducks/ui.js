import { SELECT as SELECT_FLOW } from './views/main'

export const SET_ACTIVE_MENU = 'UI_SET_ACTIVE_MENU'
export const SET_CONTENT_VIEW = 'UI_SET_CONTENT_VIEW'

const defaultState = {
    activeMenu: 'Start',
    contentView: 'ViewAuto',
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {

        case SET_ACTIVE_MENU:
            return {
                ...state,
                activeMenu: action.activeMenu,
            }

        case SELECT_FLOW:
            if (action.flowId && !action.currentSelection) {
                return {
                    ...state,
                    activeMenu: 'Flow',
                }
            }

            if (!action.flowId && state.activeMenu === 'Flow') {
                return {
                    ...state,
                    activeMenu: 'Start',
                }
            }

            return state

        case SET_CONTENT_VIEW:
            return {
                ...state,
                contentView: action.contentView,
            }

        default:
            return state
    }
}

export function setActiveMenu(activeMenu) {
    return { type: SET_ACTIVE_MENU, activeMenu }
}

export function setContentView(contentView) {
    return { type: SET_CONTENT_VIEW, contentView }
}
