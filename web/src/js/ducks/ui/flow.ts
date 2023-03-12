import * as flowActions from "../flows";
import {tabsForFlow} from "../../components/FlowView";

export const
    SET_TAB = "UI_FLOWVIEW_SET_TAB",
    SET_CONTENT_VIEW_FOR = "SET_CONTENT_VIEW_FOR",
    TOGGLE_FLOW_VIEW_TYPE = "TOGGLE_FLOW_VIEW_TYPE"


interface UiFlowState {
    tab: string
    contentViewFor: { [messageId: string]: string }
    isTreeView : boolean
}

export const defaultState: UiFlowState = {
    tab: 'request',
    contentViewFor: {},
    isTreeView: false
}

export default function reducer(state = defaultState, action): UiFlowState {
    switch (action.type) {

        case SET_CONTENT_VIEW_FOR:
            return {
                ...state,
                contentViewFor: {
                    ...state.contentViewFor,
                    [action.messageId]: action.contentView
                }
            }

        case SET_TAB:
            return {
                ...state,
                tab: action.tab ? action.tab : 'request',
            }
        case TOGGLE_FLOW_VIEW_TYPE:
            return {
                ...state,
                isTreeView: !state.isTreeView,
            }

        default:
            return state
    }
}

export function selectTab(tab) {
    return {type: SET_TAB, tab}
}

export function setContentViewFor(messageId: string, contentView: string) {
    return {type: SET_CONTENT_VIEW_FOR, messageId, contentView}
}

export function toggleFlowViewType() {
    return {type: TOGGLE_FLOW_VIEW_TYPE}
}
