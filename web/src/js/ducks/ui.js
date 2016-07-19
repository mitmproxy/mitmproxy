import { selectRelative as selectFlowRelative } from './flowView'
import { Key } from '../utils.js'
import * as flowsActions from './flows'

export const SET_ACTIVE_MENU = 'UI_SET_ACTIVE_MENU'
export const SET_CONTENT_VIEW = 'UI_SET_CONTENT_VIEW'
export const SET_SELECTED_INPUT = 'UI_SET_SELECTED_INPUT'
export const UPDATE_QUERY = 'UI_UPDATE_QUERY'
export const SELECT_TAB = 'UI_SELECT_TAB'
export const SET_PROMPT = 'UI_SET_PROMPT'
export const SET_DISPLAY_LARGE = 'UI_SET_DISPLAY_LARGE'

const defaultState = {
    activeMenu: 'Start',
    isFlowSelected: false,
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

        case flowsActions.SELECT:
            if (action.flowIds.length && !state.isFlowSelected) {
                return {
                    ...state,
                    displayLarge: false,
                    activeMenu: 'Flow',
                    isFlowSelected: true,
                }
            }

            if (!action.flowIds.length && state.isFlowSelected) {
                let activeMenu = state.activeMenu
                if (activeMenu == 'Flow') {
                    activeMenu = 'Start'
                }
                return {
                    ...state,
                    activeMenu,
                    isFlowSelected: false,
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

export function setPrompt(open) {
    return { type: SET_PROMPT, open }
}

export function setDisplayLarge(displayLarge) {
    return { type: SET_DISPLAY_LARGE, displayLarge }
}

export function onKeyDown(e) {
    if (e.ctrlKey) {
        return () => {
        }
    }
    var key = e.keyCode
    var shiftKey = e.shiftKey
    e.preventDefault()
    return (dispatch, getState) => {

        const flow = getState().flows.byId[getState().flows.selected[0]]

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
                break

            case Key.LEFT:
            {
                let tabs = ['request', 'response', 'error'].filter(k => flow[k]).concat(['details']),
                    currentTab = getState().ui.panel,
                    nextTab = tabs[(tabs.indexOf(currentTab) - 1 + tabs.length) % tabs.length]
                dispatch(selectTab(nextTab))
                break
            }

            case Key.TAB:
            case Key.RIGHT:
            {
                let tabs = ['request', 'response', 'error'].filter(k => flow[k]).concat(['details']),
                    currentTab = getState().ui.panel,
                    nextTab = tabs[(tabs.indexOf(currentTab) + 1) % tabs.length]
                dispatch(selectTab(nextTab))
                break
            }

            case Key.C:
                if (shiftKey) {
                    dispatch(flowsActions.clear())
                }
                break

            case Key.D:
            {
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

            case Key.A:
            {
                if (shiftKey) {
                    dispatch(flowsActions.acceptAll())
                } else if (flow && flow.intercepted) {
                    dispatch(flowsActions.accept(flow))
                }
                break
            }

            case Key.R:
            {
                if (!shiftKey && flow) {
                    dispatch(flowsActions.replay(flow))
                }
                break
            }

            case Key.V:
            {
                if (!shiftKey && flow && flow.modified) {
                    dispatch(flowsActions.revert(flow))
                }
                break
            }

            case Key.E:
                dispatch(setPrompt(true))
                break

            default:
                return () => {
                }
        }
    }
}
