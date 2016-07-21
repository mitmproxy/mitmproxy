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

export function uploadContent(flow, content, type){
    return (dispatch) => {
            dispatch(flowsActions.updateContent(flow, content, type)).then( () => {
            dispatch(flowsActions.updateFlow(flow))
            dispatch({ type: STOP_EDIT })
        })
    }
}

export function stopEdit(modified_flow, old_flow) {
    //make diff of modified_flow and old_flow
    return (dispatch) => {
        let flow = {...modified_flow}

        if (flow.response.content) {
            dispatch(flowsActions.updateContent(flow, flow.response.content, "response"))
            flow.response = _.omit(flow.response, "content")
        }
        if (flow.request.content) {
            dispatch(flowsActions.updateContent(flow, flow.request.content, "request"))
            flow.request = _.omit(flow.request, "content")
        }


        dispatch(flowsActions.update(flow)).then(() => {
            dispatch(flowsActions.updateFlow(flow))
            dispatch({ type: STOP_EDIT })
        })
    }
}
