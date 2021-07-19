export const HIDE_MODAL = 'UI_HIDE_MODAL'
export const SET_ACTIVE_MODAL = 'UI_SET_ACTIVE_MODAL'

const defaultState = {
    activeModal: undefined,
}

export default function reducer(state = defaultState, action){
    switch (action.type){

        case SET_ACTIVE_MODAL:
            return {
                ...state,
                activeModal: action.activeModal,
            }

        case HIDE_MODAL:
            return {
                ...state,
                activeModal: undefined
            }
        default:
            return state
    }
}

export function setActiveModal(activeModal) {
    return { type: SET_ACTIVE_MODAL, activeModal }
}

export function hideModal(){
    return { type: HIDE_MODAL }
}
