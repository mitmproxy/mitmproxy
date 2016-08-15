import * as flowsActions from '../flows'
import { getDiff } from "../../utils"

import _ from 'lodash'

export const SET_CONTENT_VIEW = 'UI_FLOWVIEW_SET_CONTENT_VIEW',
             DISPLAY_LARGE    = 'UI_FLOWVIEW_DISPLAY_LARGE',
             SET_TAB          = "UI_FLOWVIEW_SET_TAB",
             START_EDIT       = 'UI_FLOWVIEW_START_EDIT',
             UPDATE_EDIT      = 'UI_FLOWVIEW_UPDATE_EDIT',
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
            }

        case UPDATE_EDIT:
            return {
                ...state,
                modifiedFlow: _.merge({}, state.modifiedFlow, action.update)
            }

        case flowsActions.SELECT:
            return {
                ...state,
                modifiedFlow: false,
                displayLarge: false,
            }

        case flowsActions.UPDATE:
            // There is no explicit "stop edit" event.
            // We stop editing when we receive an update for
            // the currently edited flow from the server
            if (action.item.id === state.modifiedFlow.id) {
                return {
                    ...state,
                    modifiedFlow: false,
                    displayLarge: false,
                }
            } else {
                return state
            }


        case SET_TAB:
            return {
                ...state,
                tab: action.tab ? action.tab : 'request',
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

export function stopEdit(flow, modifiedFlow) {
    let diff = getDiff(flow, modifiedFlow)
    return flowsActions.update(flow, diff)
}
