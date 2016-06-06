import {fetchApi} from "../../utils"

export const ADD = "ADD"
export const UPDATE = "UPDATE"
export const REMOVE = "REMOVE"
export const REQUEST_LIST = "REQUEST_LIST"
export const RECEIVE_LIST = "RECEIVE_LIST"


const defaultState = {
    list: [],
    isFetching: false,
    actionsDuringFetch: [],
    byId: {},
    indexOf: {},
}

export default function makeList(actionType, fetchURL) {
    function reduceList(state = defaultState, action = {}) {

        if (action.type !== actionType) {
            return state
        }

        // Handle cases where we finished fetching or are still fetching.
        if (action.cmd === RECEIVE_LIST) {
            let s = {
                isFetching: false,
                actionsDuringFetch: [],
                list: action.list,
                byId: {},
                indexOf: {}
            }
            for (let i = 0; i < action.list.length; i++) {
                let item = action.list[i]
                s.byId[item.id] = item
                s.indexOf[item.id] = i
            }
            for (action of state.actionsDuringFetch) {
                s = reduceList(s, action)
            }
            return s
        } else if (state.isFetching) {
            return {
                ...state,
                actionsDuringFetch: [...state.actionsDuringFetch, action]
            }
        }

        let list, itemIndex
        switch (action.cmd) {
            case ADD:
                return {
                    list: [...state.list, action.item],
                    byId: {...state.byId, [action.item.id]: action.item},
                    indexOf: {...state.indexOf, [action.item.id]: state.list.length},
                }

            case UPDATE:

                list = [...state.list]
                itemIndex = state.indexOf[action.item.id]
                list[itemIndex] = action.item
                return {
                    ...state,
                    list
                }

            case REMOVE:
                list = [...state.list]
                itemIndex = state.indexOf[action.item.id]
                list.splice(itemIndex, 1)
                return {
                    ...state,
                    list,
                    byId: {...state.byId, [action.item.id]: undefined},
                    indexOf: {...state.indexOf, [action.item.id]: undefined},
                }

            case REQUEST_LIST:
                return {
                    ...state,
                    isFetching: true
                }

            default:
                console.debug("unknown action", action)
                return state
        }
    }

    function addItem(item) {
        return {
            type: actionType,
            cmd: ADD,
            item
        }
    }

    function updateItem(item) {
        return {
            type: actionType,
            cmd: UPDATE,
            item
        }
    }

    function removeItem(item) {
        return {
            type: actionType,
            cmd: REMOVE,
            item
        }
    }


    function updateList(event) {
        /* This action creater takes all WebSocket events */
        return dispatch => {
            switch (event.cmd) {
                case "add":
                    return dispatch(addItem(event.data))
                case "update":
                    return dispatch(updateItem(event.data))
                case "remove":
                    return dispatch(removeItem(event.data))
                case "reset":
                    return dispatch(fetchList())
                default:
                    console.error("unknown list update", event)
            }
        }
    }

    function requestList() {
        return {
            type: actionType,
            cmd: REQUEST_LIST,
        }
    }

    function receiveList(list) {
        return {
            type: actionType,
            cmd: RECEIVE_LIST,
            list
        }
    }

    function fetchList() {
        return dispatch => {

            dispatch(requestList())

            return fetchApi(fetchURL).then(response => {
                return response.json().then(json => {
                    dispatch(receiveList(json.data))
                })
            })
        }
    }


    return {reduceList, updateList, fetchList, addItem, updateItem, removeItem,}
}