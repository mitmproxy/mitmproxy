export const SET_TAB = "UI_FLOWVIEW_SET_TAB";
export const SET_CONTENT_VIEW_FOR = "SET_CONTENT_VIEW_FOR";

interface UiFlowState {
    tab: string;
    contentViewFor: { [messageId: string]: string };
}

export const defaultState: UiFlowState = {
    tab: "request",
    contentViewFor: {},
};

export default function reducer(state = defaultState, action): UiFlowState {
    switch (action.type) {
        case SET_CONTENT_VIEW_FOR:
            return {
                ...state,
                contentViewFor: {
                    ...state.contentViewFor,
                    [action.messageId]: action.contentView,
                },
            };

        case SET_TAB:
            return {
                ...state,
                tab: action.tab ? action.tab : "request",
            };

        default:
            return state;
    }
}

export function selectTab(tab) {
    return { type: SET_TAB, tab };
}

export function setContentViewFor(messageId: string, contentView: string) {
    return { type: SET_CONTENT_VIEW_FOR, messageId, contentView };
}
