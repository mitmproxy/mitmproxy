import { select, setFilter, setHighlight } from "./ducks/flows"
import { selectTab } from "./ducks/ui/flow"
import { toggleVisibility } from "./ducks/eventLog"

const Query = {
    SEARCH: "s",
    HIGHLIGHT: "h",
    SHOW_EVENTLOG: "e"
};

function updateStoreFromUrl(store) {
    const [path, query]   = window.location.hash.substr(1).split("?", 2)
    const path_components = path.substr(1).split("/")

    if (path_components[0] === "flows") {
        if (path_components.length == 3) {
            const [flowId, tab] = path_components.slice(1)
            store.dispatch(select(flowId))
            store.dispatch(selectTab(tab))
        }
    }

    if (query) {
        query
            .split("&")
            .forEach((x) => {
                const [key, value] = x.split("=", 2)
                switch (key) {
                    case Query.SEARCH:
                        store.dispatch(setFilter(value))
                        break
                    case Query.HIGHLIGHT:
                        store.dispatch(setHighlight(value))
                        break
                    case Query.SHOW_EVENTLOG:
                        if (!store.getState().eventLog.visible)
                            store.dispatch(toggleVisibility())
                        break
                    default:
                        console.error(`unimplemented query arg: ${x}`)
                }
            })
    }
}

function updateUrlFromStore(store) {
    const state    = store.getState()
    let query      = {
        [Query.SEARCH]: state.flows.filter,
        [Query.HIGHLIGHT]: state.flows.highlight,
        [Query.SHOW_EVENTLOG]: state.eventLog.visible,
    }
    const queryStr = Object.keys(query)
        .filter(k => query[k])
        .map(k => `${k}=${query[k]}`)
        .join("&")

    let url
    if (state.flows.selected.length > 0) {
        url = `/flows/${state.flows.selected[0]}/${state.ui.flow.tab}`
    } else {
        url = "/flows"
    }

    if (queryStr) {
        url += "?" + queryStr
    }
    if (window.location.hash !== url) {
        // FIXME: replace state
        window.location.hash = url
    }
}

export default function initialize(store) {
    updateStoreFromUrl(store)
    store.subscribe(() => updateUrlFromStore(store))
}
