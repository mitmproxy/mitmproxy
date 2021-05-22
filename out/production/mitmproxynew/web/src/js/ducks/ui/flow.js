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
    viewDescription: '',
    showFullContent: false,
    modifiedFlow: false,
    contentView: 'Auto',
    tab: 'request',
    content: [],
    maxContentLines: 80,
}

export default function reducer(state = defaultState, action) {
    let wasInEditMode = state.modifiedFlow

    let content = action.content || state.content
    let isFullContentShown = content && content.length <= state.maxContentLines

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
                showFullContent: isFullContentShown,
            }

        case flowsActions.UPDATE:
            // There is no explicit "stop edit" event.
            // We stop editing when we receive an update for
            // the currently edited flow from the server
            if (action.data.id === state.modifiedFlow.id) {
                return {
                    ...state,
                    modifiedFlow: false,
                    displayLarge: false,
                    contentView: (wasInEditMode ? 'Auto' : state.contentView),
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
                showFullContent: true
            }

        case SET_TAB:
            return {
                ...state,
                tab: action.tab ? action.tab : 'request',
                displayLarge: false,
                showFullContent: state.contentView === 'Edit'
            }

        case SET_CONTENT_VIEW:
            return {
                ...state,
                contentView: action.contentView,
                showFullContent: action.contentView === 'Edit'
            }

        case SET_CONTENT:
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

export function setShowFullContent() {
    return { type: SET_SHOW_FULL_CONTENT }
}

export function setContent(content){
    return { type: SET_CONTENT, content }
}

export function stopEdit(flow, modifiedFlow) {
    return flowsActions.update(flow, getDiff(flow, modifiedFlow))
}
