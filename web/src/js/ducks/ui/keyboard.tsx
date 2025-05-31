import { selectRequestTab, selectResponseTab } from "./flow";
import * as flowsActions from "../flows";
import * as modalActions from "./modal";
import { runCommand } from "../../utils";
import { AppDispatch, RootState } from "../store";
import { tabsForFlow, tabsForFlowNext } from "./utils";

export function onKeyDown(e: KeyboardEvent) {
    //console.debug("onKeyDown", e)
    if (e.ctrlKey || e.metaKey) {
        return () => {};
    }
    const key = e.key;
    e.preventDefault();
    return (dispatch: AppDispatch, getState: () => RootState) => {
        const { flows } = getState();
        const selectedFlows = flows.selected;
        const flow = selectedFlows[0];

        switch (key) {
            case "k":
            case "ArrowUp":
                dispatch(flowsActions.selectRelative(flows, -1));
                break;

            case "j":
            case "ArrowDown":
                dispatch(flowsActions.selectRelative(flows, +1));
                break;

            case " ":
            case "PageDown":
                dispatch(flowsActions.selectRelative(flows, +10));
                break;

            case "PageUp":
                dispatch(flowsActions.selectRelative(flows, -10));
                break;

            case "End":
                dispatch(flowsActions.selectRelative(flows, +1e10));
                break;

            case "Home":
                dispatch(flowsActions.selectRelative(flows, -1e10));
                break;

            case "Escape":
                if (getState().ui.modal.activeModal) {
                    dispatch(modalActions.hideModal());
                } else {
                    dispatch(flowsActions.select([]));
                }
                break;

            case "ArrowLeft": {
                if (!flow) break;

                const currentRequestTab = getState().ui.flow.tabRequest;
                const currentResponseTab = getState().ui.flow.tabResponse;

                const getNextTab = (tabs: string[]) => {
                    return tabs[
                        (Math.max(0, tabs.indexOf(currentResponseTab)) -
                            1 +
                            tabs.length) %
                            tabs.length
                    ];
                };

                // mitmweb does not have a request tab and non-http flow types don't either.
                if (!currentRequestTab) {
                    const tabs = tabsForFlow(flow);
                    const nextTab = getNextTab(tabs);
                    return dispatch(selectResponseTab(nextTab));
                } else {
                    const { request: requestTabs, response: responseTabs } =
                        tabsForFlowNext(flow);
                    const tabs = [...requestTabs, ...responseTabs];
                    const nextTab = getNextTab(tabs);
                    return dispatch(
                        requestTabs.includes(nextTab)
                            ? selectRequestTab(nextTab)
                            : selectResponseTab(nextTab),
                    );
                }
            }
            case "Tab":
            case "ArrowRight": {
                if (!flow) break;

                const currentRequestTab = getState().ui.flow.tabRequest;
                const currentResponseTab = getState().ui.flow.tabResponse;

                const getNextTab = (tabs: string[]) => {
                    return tabs[
                        (Math.max(0, tabs.indexOf(currentResponseTab)) + 1) %
                            tabs.length
                    ];
                };

                // mitmweb does not have a request tab and non-http flow types don't either.
                if (!currentRequestTab) {
                    const tabs = tabsForFlow(flow);
                    const nextTab = getNextTab(tabs);
                    return dispatch(selectResponseTab(nextTab));
                } else {
                    const { request: requestTabs, response: responseTabs } =
                        tabsForFlowNext(flow);
                    const tabs = [...requestTabs, ...responseTabs];
                    const nextTab = getNextTab(tabs);
                    return dispatch(
                        requestTabs.includes(nextTab)
                            ? selectRequestTab(nextTab)
                            : selectResponseTab(nextTab),
                    );
                }
            }

            case "Delete":
            case "d": {
                dispatch(flowsActions.remove(selectedFlows));
                break;
            }

            case "n": {
                runCommand("view.flows.create", "get", "https://example.com/");
                break;
            }

            case "D": {
                dispatch(flowsActions.duplicate(selectedFlows));
                break;
            }
            case "a": {
                dispatch(flowsActions.resume(selectedFlows));
                break;
            }
            case "A": {
                dispatch(flowsActions.resumeAll());
                break;
            }

            case "r": {
                dispatch(flowsActions.replay(selectedFlows));
                break;
            }

            case "v": {
                dispatch(flowsActions.revert(selectedFlows));
                break;
            }

            case "x": {
                dispatch(flowsActions.kill(selectedFlows));
                break;
            }

            case "X": {
                dispatch(flowsActions.killAll());
                break;
            }

            case "z": {
                dispatch(flowsActions.clear());
                break;
            }

            default:
                return;
        }
    };
}
