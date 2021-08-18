import {Reducer} from "redux";

export const
    SET_TAB = "UI_FLOWVIEW_SET_TAB",
    SET_CONTENT_VIEW_FOR = "SET_CONTENT_VIEW_FOR"


interface UiFlowState {
    tab: string
    contentViewFor: { [messageId: string]: string }
}

const defaultState: UiFlowState = {
    tab: 'request',
    contentViewFor: {},
}

const reducer: Reducer<UiFlowState> = (state = defaultState, action): UiFlowState => {

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

        default:
            return state
    }
}
export default reducer;

export function selectTab(tab) {
    return {type: SET_TAB, tab}
}

export function setContentViewFor(messageId: string, contentView: string) {
    return {type: SET_CONTENT_VIEW_FOR, messageId, contentView}
}
