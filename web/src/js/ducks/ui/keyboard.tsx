import { selectRequestTab, selectTab } from "./flow";
import * as flowsActions from "../flows";
import * as modalActions from "./modal";
import { splitTabsForFlow, tabsForFlow } from "../../components/FlowView";
import { runCommand } from "../../utils";
import type { AppDispatch, RootState } from "../store";
import type { Flow } from "../../flow";

function relativeTab<T extends string>(
    tabs: T[],
    current: string,
    step: number,
): T {
    const index = Math.max(
        0,
        tabs.findIndex((tab) => tab === current),
    );
    return tabs[(index + step + tabs.length) % tabs.length];
}

// The split view's response panel is left alone: it has a second tab only for WebSocket flows.
function selectRelativeTab(flow: Flow, state: RootState, step: number) {
    if (flow.type === "http" && state.options.web_split_flowview) {
        const tabs = splitTabsForFlow(flow).request;
        return selectRequestTab(
            relativeTab(tabs, state.ui.flow.tabRequest, step),
        );
    }
    return selectTab(relativeTab(tabsForFlow(flow), state.ui.flow.tab, step));
}

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
                dispatch(selectRelativeTab(flow, getState(), -1));
                break;
            }

            case "Tab":
            case "ArrowRight": {
                if (!flow) break;
                dispatch(selectRelativeTab(flow, getState(), +1));
                break;
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
