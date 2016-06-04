import {fetchApi} from "../../utils";

export const ADD = "ADD"
export const REQUEST_LIST = "REQUEST_LIST"
export const RECEIVE_LIST = "RECEIVE_LIST"


const defaultState = {
    list: [],
    isFetching: false,
    actionsDuringFetch: [],
    byId: {},
    indexOf: {},
};

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

        switch (action.cmd) {
            case ADD:
                return {
                    list: [...state.list, action.item],
                    byId: {...state.byId, [action.item.id]: action.item},
                    indexOf: {...state.indexOf, [action.item.id]: state.list.length},
                }

            case REQUEST_LIST:
                return {
                    ...defaultState,
                    isFetching: true
                }

            default:
                console.debug("unknown action", action.type)
                return state
        }
    }

    function addToList(item) {
        return {
            type: actionType,
            cmd: ADD,
            item
        }
    }


    function updateList(action) {
        /* This action creater takes all WebSocket events */
        return dispatch => {
            switch (action.cmd) {
                case "add":
                    return dispatch(addToList(action.data))
                case "reset":
                    return dispatch(fetchList())
                default:
                    console.error("unknown list update", action)
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

            fetchApi(fetchURL).then(response => {
                return response.json().then(json => {
                    dispatch(receiveList(json.data))
                })
            })
        }
    }


    return {reduceList, addToList, updateList, fetchList}
}