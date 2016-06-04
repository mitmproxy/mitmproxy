import makeList from "./utils/list"

export const UPDATE_FLOWS = "UPDATE_FLOWS"

const {
    reduceList,
    updateList,
    fetchList,
} = makeList(UPDATE_FLOWS, "/flows")


const defaultState = {
    all: reduceList(),
}

export default function reducer(state = defaultState, action) {
    switch (action.type) {
        case UPDATE_FLOWS:
            let all = reduceList(state.all, action)
            return {
                ...state,
                all,
            }
        default:
            return state
    }
}

export {updateList as updateFlows, fetchList as fetchFlows}