import * as flowsActions from '../flows'
import { getDiff } from "../../utils"

import _ from 'lodash'

export const SET_CONTENT_VIEW               = 'UI_FLOWVIEW_SET_CONTENT_VIEW',
             DISPLAY_LARGE                  = 'UI_FLOWVIEW_DISPLAY_LARGE',
             SET_TAB                        = "UI_FLOWVIEW_SET_TAB",
             START_EDIT                     = 'UI_FLOWVIEW_START_EDIT',
             UPDATE_EDIT                    = 'UI_FLOWVIEW_UPDATE_EDIT',
             UPLOAD_CONTENT                 = 'UI_FLOWVIEW_UPLOAD_CONTENT',
             SET_SHOW_FULL_CONTENT          = 'UI_SET_SHOW_FULL_CONTENT',
             SET_CONTENT_VIEW_DESCRIPTION   = "UI_SET_CONTENT_VIEW_DESCRIPTION",
             SET_CONTENT                    = "UI_SET_CONTENT"


const defaultState = {
    displayLarge: false,
    contentViewDescription: '',
    showFullContent: false,
    modifiedFlow: false,
    contentView: 'Auto',
    tab: 'request',
    content: [],
    maxContentLines: 80,
}

export default function reducer(state = defaultState, action) {
    let wasInEditMode = !!(state.modifiedFlow)
    switch (action.type) {

        case START_EDIT:
            return {
                ...state,
                modifiedFlow: action.flow,
                contentView: 'Edit',
                showFullContent: true
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
                contentView: (wasInEditMode ? 'Auto' : state.contentView),
                viewDescription: '',
                showFullContent: false,
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
                    contentView: (wasInEditMode ? 'Auto' : state.contentView),
                    viewDescription: '',
                    showFullContent: false
                }
            } else {
                return state
            }

        case SET_CONTENT_VIEW_DESCRIPTION:
            return {
                ...state,
                viewDescription: action.description
            }

        case SET_SHOW_FULL_CONTENT:
            return {
                ...state,
                showFullContent: action.show
            }

        case SET_TAB:
            return {
                ...state,
                tab: action.tab,
                displayLarge: false,
                showFullContent: false
            }

        case SET_CONTENT_VIEW:
            return {
                ...state,
                contentView: action.contentView,
                showFullContent: action.contentView == 'Edit'
            }

        case SET_CONTENT:
            let isFullContentShown = action.content.length < state.maxContentLines
            return {
                ...state,
                content: action.content,
                showFullContent: isFullContentShown
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

export function setContentViewDescription(description) {
    return { type: SET_CONTENT_VIEW_DESCRIPTION, description }
}

export function setShowFullContent(show) {
    return { type: SET_SHOW_FULL_CONTENT, show }
}

export function updateEdit(update) {
    return { type: UPDATE_EDIT, update }
}

export function setContent(content){
    return { type: SET_CONTENT, content}
}

export function stopEdit(flow, modifiedFlow) {
    let diff = getDiff(flow, modifiedFlow)
    return flowsActions.update(flow, diff)
}
