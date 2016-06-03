export const ADD = 'add'

const defaultState = {
    list: [],
    //isFetching: false,
    //updateBeforeFetch: [],
    indexOf: {},
    //views: {}
};

export default function getList(state = defaultState, action = {}) {
    switch (action.cmd) {
        case ADD:
            return {
                list: [...state.list, action.data],
                indexOf: {...state.indexOf, [action.data.id]: state.list.length},
            }
        default:
            return state
    }
}