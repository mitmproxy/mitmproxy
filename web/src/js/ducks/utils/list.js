import _ from 'lodash'

export const ADD = 'LIST_ADD'
export const UPDATE = 'LIST_UPDATE'
export const REMOVE = 'LIST_REMOVE'
export const RECEIVE = 'LIST_RECEIVE'

const defaultState = {
    data: [],
    byId: {},
    indexOf: {},
}

export default function reduce(state = defaultState, action) {
    switch (action.type) {

        case ADD:
            return {
                ...state,
                data: [...state.data, action.item],
                byId: { ...state.byId, [action.item.id]: action.item },
                indexOf: { ...state.indexOf, [action.item.id]: state.data.length },
            }

        case UPDATE: {
            const data = [...state.data]
            const index = state.indexOf[action.id]

            // FIXME: We should just swallow this
            if (index == null) {
                throw new Error('Item not found')
            }

            data[index] = action.item

            return {
                ...state,
                data,
                byId: { ...state.byId, [action.item.id]: action.item },
            }
        }

        case REMOVE: {
            const data = [...state.data]
            const indexOf = { ...state.indexOf }
            const index = indexOf[action.id]

            // FIXME: We should just swallow this
            if (index == null) {
                throw new Error('Item not found')
            }

            data.splice(index, 1)
            for (let i = data.length - 1; i >= index; i--) {
                indexOf[data[i].id] = i
            }

            return {
                ...state,
                data,
                indexOf,
                byId: { ...state.byId, [action.id]: null },
            }
        }

        case RECEIVE:
            return {
                ...state,
                data: action.list,
                byId: _.fromPairs(action.list.map(item => [item.id, item])),
                indexOf: _.fromPairs(action.list.map((item, index) => [item.id, index])),
            }

        default:
            return state
    }
}

/**
 * @public
 */
export function add(item) {
    return { type: ADD, item }
}

/**
 * @public
 */
export function update(id, item) {
    return { type: UPDATE, id, item }
}

/**
 * @public
 */
export function remove(id) {
    return { type: REMOVE, id }
}

/**
 * @public
 */
export function receive(list) {
    return { type: RECEIVE, list }
}
