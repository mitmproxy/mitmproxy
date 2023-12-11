export const TOGGLE_VISIBILITY = "COMMANDBAR_TOGGLE_VISIBILITY";

interface CommandBarState {
    visible: boolean;
}

export const defaultState: CommandBarState = {
    visible: false,
};

export default function reducer(state = defaultState, action): CommandBarState {
    switch (action.type) {
        case TOGGLE_VISIBILITY:
            return {
                ...state,
                visible: !state.visible,
            };

        default:
            return state;
    }
}

export function toggleVisibility() {
    return { type: TOGGLE_VISIBILITY };
}
