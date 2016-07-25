export const SET_EDIT_TYPE = 'SET_EDIT_TYPE'
export const SET_SELECTED_INPUT = 'SET_SELECTED_INPUT'

const defaultState = {
    editType: null,
    selectedInput: null,
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {

        case SET_EDIT_TYPE:
            return {
                ...state,
                editType: action.editType,
            }

        case SET_SELECTED_INPUT:
            return {
                ...state,
                selectedInput: action.selectedInput,
            }

        default:
            return state
    }
}

export function setEditType(editType) {
    return { type: SET_EDIT_TYPE, editType }
}

export function setSelectedInput(selectedInput) {
    return { type: SET_SELECTED_INPUT, selectedInput }
}
