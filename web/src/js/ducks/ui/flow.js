import * as flowsActions from '../flows'
import _ from 'lodash'

export const SET_CONTENT_VIEW = 'UI_FLOWVIEW_SET_CONTENT_VIEW',
             DISPLAY_LARGE    = 'UI_FLOWVIEW_DISPLAY_LARGE',
             SET_TAB          = "UI_FLOWVIEW_SET_TAB",
             START_EDIT       = 'UI_FLOWVIEW_START_EDIT',
             UPDATE_EDIT      = 'UI_FLOWVIEW_UPDATE_EDIT',
             STOP_EDIT        = 'UI_FLOWVIEW_STOP_EDIT'


const defaultState = {
    displayLarge: false,
    modifiedFlow: false,
    contentView: 'ViewAuto',
    tab: 'request',
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {

        case START_EDIT:
            return {
                ...state,
                modifiedFlow: action.flow
            }

        case UPDATE_EDIT:
            return {
                ...state,
                modifiedFlow: _.merge({}, state.modifiedFlow, action.update)
            }

        case STOP_EDIT:
            return {
                ...state,
                modifiedFlow: false
            }

        case flowsActions.SELECT:
            return {
                ...state,
                modifiedFlow: false,
                displayLarge: false,
            }

        case SET_TAB:
            return {
                ...state,
                tab: action.tab,
                displayLarge: false,
            }

        case SET_CONTENT_VIEW:
            return {
                ...state,
                contentView: action.contentView,
            }

        case DISPLAY_LARGE:
            return {
                ...state,
                displayLarge: true,
            }
        default:
            return state
    }
}

export function setContentView(contentView) {
    return { type: SET_CONTENT_VIEW, contentView }
}

export function displayLarge() {
    return { type: DISPLAY_LARGE }
}

export function selectTab(tab) {
    return { type: SET_TAB, tab }
}

export function startEdit(flow) {
    return { type: START_EDIT, flow }
}

export function updateEdit(update) {
    return { type: UPDATE_EDIT, update }
}

export function stopEdit(flow) {
    return (dispatch) => {
        dispatch(flowsActions.update(flow, flow)).then(() => {
            dispatch(flowsActions.updateFlow(flow))
            dispatch({ type: STOP_EDIT })
        })
    }
}
