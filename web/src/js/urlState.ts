/**
 * Instead of dealing with react-router's ever-changing APIs,
 * we use a simple url state manager where we only
 *
 * - read the initial URL state on page load
 * - push updates to the URL later on.
 */
import { select, setFilter, setHighlight } from "./ducks/flows";
import { selectTab } from "./ducks/ui/flow";
import * as eventLogActions from "./ducks/eventLog";
import * as commandBarActions from "./ducks/commandBar";
import { RootStore } from "./ducks/store";
import { Tab, setCurrent } from "./ducks/ui/tabs";

const Query = {
    SEARCH: "s",
    HIGHLIGHT: "h",
    SHOW_EVENTLOG: "e",
    SHOW_COMMANDBAR: "c",
};

export function updateStoreFromUrl(store: RootStore) {
    const [path, query] = window.location.hash.substr(1).split("?", 2);
    const path_components = path.substr(1).split("/");

    if (path_components[0] === "flows") {
        if (path_components.length == 3) {
            const [flowId, tab] = path_components.slice(1);
            store.dispatch(selectTab(tab));

            const selectFlowOnceAvailable = () => {
                const flow = store.getState().flows.byId[flowId];
                if (flow !== undefined) {
                    unsubscribe();
                    store.dispatch(select([flow]));
                }
            };
            const unsubscribe = store.subscribe(selectFlowOnceAvailable);
            selectFlowOnceAvailable();
        }
    } else if (path_components[0] === "capture") {
        store.dispatch(setCurrent(Tab.Capture));
    }

    if (query) {
        query.split("&").forEach((x) => {
            const [key, encodedVal] = x.split("=", 2);
            const value = decodeURIComponent(encodedVal);
            switch (key) {
                case Query.SEARCH:
                    store.dispatch(setFilter(value));
                    break;
                case Query.HIGHLIGHT:
                    store.dispatch(setHighlight(value));
                    break;
                case Query.SHOW_EVENTLOG:
                    if (!store.getState().eventLog.visible)
                        store.dispatch(eventLogActions.toggleVisibility());
                    break;
                case Query.SHOW_COMMANDBAR:
                    if (!store.getState().commandBar.visible)
                        store.dispatch(commandBarActions.toggleVisibility());
                    break;
                default:
                    console.error(`unimplemented query arg: ${x}`);
            }
        });
    }
}

export function updateUrlFromStore(store: RootStore) {
    const state = store.getState();
    const query = {
        [Query.SEARCH]: state.flows.filter,
        [Query.HIGHLIGHT]: state.flows.highlight,
        [Query.SHOW_EVENTLOG]: state.eventLog.visible,
        [Query.SHOW_COMMANDBAR]: state.commandBar.visible,
    };
    const queryStr = Object.keys(query)
        .filter((k) => query[k])
        .map((k) => `${k}=${encodeURIComponent(query[k]!)}`)
        .join("&");

    let url;
    if (state.ui.tabs.current === Tab.Capture) {
        url = "/capture";
    } else if (state.flows.selected.length > 0) {
        url = `/flows/${state.flows.selected[0].id}/${state.ui.flow.tab}`;
    } else {
        url = "/flows";
    }

    if (queryStr) {
        url += "?" + queryStr;
    }
    let pathname = window.location.pathname;
    if (pathname === "blank") {
        pathname = "/"; // this happens in tests...
    }
    if (window.location.hash.substr(1) !== url) {
        history.replaceState(undefined, "", `${pathname}#${url}`);
    }
}

export default function initialize(store) {
    updateStoreFromUrl(store);
    store.subscribe(() => updateUrlFromStore(store));
}
