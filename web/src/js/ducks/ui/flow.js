import * as flowsActions from '../flows'
import { getDiff } from "../../utils"

import _ from 'lodash'

export const SET_CONTENT_VIEW = 'UI_FLOWVIEW_SET_CONTENT_VIEW',
             DISPLAY_LARGE    = 'UI_FLOWVIEW_DISPLAY_LARGE',
             SET_TAB          = "UI_FLOWVIEW_SET_TAB",
             START_EDIT       = 'UI_FLOWVIEW_START_EDIT',
             UPDATE_EDIT      = 'UI_FLOWVIEW_UPDATE_EDIT',
             STOP_EDIT        = 'UI_FLOWVIEW_STOP_EDIT',
             UPLOAD_CONTENT   = 'UI_FLOWVIEW_UPLOAD_CONTENT'


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
                modifiedFlow: action.flow,
                contentView: 'ViewRaw'
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

export function stopEdit(flow, modified_flow) {
    let diff = getDiff(flow, modified_flow)
    return (dispatch) => {
        if (diff.response && diff.response.content) {
            dispatch(flowsActions.updateContent(flow, diff.response.content, "response"))
            delete diff.response.content
        }
        if (diff.request && diff.request.content) {
            dispatch(flowsActions.updateContent(flow, diff.request.content, "request"))
            delete diff.request.content
        }

        dispatch(flowsActions.update(flow, diff)).then(() => {
            dispatch(flowsActions.updateFlow(modified_flow))
            dispatch({ type: STOP_EDIT })
        })
    }
}
