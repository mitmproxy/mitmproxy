import { SELECT as SELECT_FLOW, selectRelative as selectFlowRelative } from './views/main'
import { Key } from '../utils.js'
import * as flowsActions from '../ducks/flows'

export const SET_ACTIVE_MENU = 'UI_SET_ACTIVE_MENU'
export const SET_CONTENT_VIEW = 'UI_SET_CONTENT_VIEW'
export const SET_SELECTED_INPUT = 'UI_SET_SELECTED_INPUT'
export const UPDATE_QUERY = 'UI_UPDATE_QUERY'
export const SELECT_TAB = 'UI_SELECT_TAB'
export const SELECT_TAB_RELATIVE = 'UI_SELECT_TAB_RELATIVE'
export const SET_PROMPT = 'UI_SET_PROMPT'
export const SET_DISPLAY_LARGE = 'UI_SET_DISPLAY_LARGE'

const defaultState = {
    activeMenu: 'Start',
    selectedInput: null,
    displayLarge: false,
    promptOpen: false,
    contentView: 'ViewAuto',
    query: {},
    panel: 'request'
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
                    displayLarge: false,
                    activeMenu: 'Flow',
                }
            }

            if (!action.flowId && state.activeMenu === 'Flow') {
                return {
                    ...state,
                    displayLarge: false,
                    activeMenu: 'Start',
                }
            }

            return {
                ...state,
                displayLarge: false,
            }

        case SET_CONTENT_VIEW:
            return {
                ...state,
                contentView: action.contentView,
            }

        case SET_SELECTED_INPUT:
            return {
                ...state,
                selectedInput: action.input
            }

        case UPDATE_QUERY:
            return {
                ...state,
                query: { ...state.query, ...action.query }
            }

        case SELECT_TAB:
            return {
                ...state,
                panel: action.panel
            }

        case SELECT_TAB_RELATIVE:
            if (!action.flow || action.shift === null) {
                return {
                    ...state,
                    panel: 'request'
                }
            }
            const tabs = ['request', 'response', 'error'].filter(k => action.flow[k]).concat(['details'])
            return {
                ...state,
                panel: tabs[(tabs.indexOf(state.panel) + action.shift + tabs.length) % tabs.length]
            }

        case SET_PROMPT:
            return {
                ...state,
                promptOpen: action.open,
            }

        case SET_DISPLAY_LARGE:
            return {
                ...state,
                displayLarge: action.displayLarge,
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

export function setSelectedInput(input) {
    return { type: SET_SELECTED_INPUT, input }
}

export function updateQuery(query) {
    return { type: UPDATE_QUERY, query }
}

export function selectTab(panel) {
    return { type: SELECT_TAB, panel }
}

export function selectTabRelative(shift) {
    return (dispatch, getState) => {
        let flow = getState().flows.list.byId[getState().flows.views.main.selected[0]]
        dispatch({ type: SELECT_TAB_RELATIVE, shift, flow })
    }
}

export function setPrompt(open) {
    return { type: SET_PROMPT, open }
}

export function setDisplayLarge(displayLarge) {
    return { type: SET_DISPLAY_LARGE, displayLarge }
}

export function onKeyDown(key, shiftKey) {
    return (dispatch, getState) => {
        switch (key) {

            case Key.I:
                dispatch(setSelectedInput('intercept'))
                break

            case Key.L:
                dispatch(setSelectedInput('search'))
                break

            case Key.H:
                dispatch(setSelectedInput('highlight'))
                break

            case Key.K:
            case Key.UP:
                dispatch(selectFlowRelative(-1))
                break

            case Key.J:
            case Key.DOWN:
                dispatch(selectFlowRelative(+1))
                break

            case Key.SPACE:
            case Key.PAGE_DOWN:
                dispatch(selectFlowRelative(+10))
                break

            case Key.PAGE_UP:
                dispatch(selectFlowRelative(-10))
                break

            case Key.END:
                dispatch(selectFlowRelative(+1e10))
                break

            case Key.HOME:
                dispatch(selectFlowRelative(-1e10))
                break

            case Key.ESC:
                dispatch(selectFlowRelative(null))
                dispatch(selectTabRelative(null))
                break

            case Key.H:
            case Key.LEFT:
                dispatch(selectTabRelative(-1))
                break

            case Key.L:
            case Key.TAB:
            case Key.RIGHT:
                dispatch(selectTabRelative(+1))
                break

            case Key.C:
                if (shiftKey) {
                    dispatch(flowsActions.clear())
                }
                break

            case Key.D: {
                const flow = getState().flows.list.byId[getState().flows.views.main.selected[0]]
                if (!flow) {
                    return
                }
                if (shiftKey) {
                    dispatch(flowsActions.duplicate(flow))
                } else {
                    dispatch(flowsActions.remove(flow))
                }
                break
            }

            case Key.A: {
                const flow = getState().flows.list.byId[getState().flows.views.main.selected[0]]
                if (shiftKey) {
                    dispatch(flowsActions.acceptAll())
                } else if (flow && flow.intercepted) {
                    dispatch(flowsActions.accept(flow))
                }
                break
            }

            case Key.R: {
                const flow = getState().flows.list.byId[getState().flows.views.main.selected[0]]
                if (!shiftKey && flow) {
                    dispatch(flowsActions.replay(flow))
                }
                break
            }

            case Key.V: {
                const flow = getState().flows.list.byId[getState().flows.views.main.selected[0]]
                if (!shiftKey && flow && flow.modified) {
                    dispatch(flowsActions.revert(flow))
                }
                break
            }

            case Key.E:
                dispatch(setPrompt(true))
                break

            default:
                return () => {}
        }
        event.preventDefault()
    }
}
