import { Key } from "../../utils"
import { selectTab } from "./flow"
import * as flowsActions from "../flows"
import * as modalActions from "./modal"


export function onKeyDown(e) {
    //console.debug("onKeyDown", e)
    if (e.ctrlKey || e.metaKey) {
        return () => {
        }
    }
    let key      = e.keyCode,
        shiftKey = e.shiftKey
    e.preventDefault()
    return (dispatch, getState) => {

        const flows = getState().flows,
              flow = flows.byId[getState().flows.selected[0]]

        switch (key) {
            case Key.K:
            case Key.UP:
                dispatch(flowsActions.selectRelative(flows, -1))
                break

            case Key.J:
            case Key.DOWN:
                dispatch(flowsActions.selectRelative(flows, +1))
                break

            case Key.SPACE:
            case Key.PAGE_DOWN:
                dispatch(flowsActions.selectRelative(flows, +10))
                break

            case Key.PAGE_UP:
                dispatch(flowsActions.selectRelative(flows, -10))
                break

            case Key.END:
                dispatch(flowsActions.selectRelative(flows, +1e10))
                break

            case Key.HOME:
                dispatch(flowsActions.selectRelative(flows, -1e10))
                break

            case Key.ESC:
                if(getState().ui.modal.activeModal){
                    dispatch(modalActions.hideModal())
                } else {
                    dispatch(flowsActions.select(null))
                }
                break

            case Key.LEFT: {
                if (!flow) break
                let tabs       = ['request', 'response', 'error'].filter(k => flow[k]).concat(['details']),
                    currentTab = getState().ui.flow.tab,
                    nextTab    = tabs[(tabs.indexOf(currentTab) - 1 + tabs.length) % tabs.length]
                dispatch(selectTab(nextTab))
                break
            }

            case Key.TAB:
            case Key.RIGHT: {
                if (!flow) break
                let tabs       = ['request', 'response', 'error'].filter(k => flow[k]).concat(['details']),
                    currentTab = getState().ui.flow.tab,
                    nextTab    = tabs[(tabs.indexOf(currentTab) + 1) % tabs.length]
                dispatch(selectTab(nextTab))
                break
            }

            case Key.D: {
                if (!flow) {
                    return
                }
                if (shiftKey) {
                    dispatch(flowsActions.duplicate(flow))
                } else {
                    dispatch(flowsActions.remove(flow))
                }
                break
            }

            case Key.A: {
                if (shiftKey) {
                    dispatch(flowsActions.resumeAll())
                } else if (flow && flow.intercepted) {
                    dispatch(flowsActions.resume(flow))
                }
                break
            }

            case Key.R: {
                if (!shiftKey && flow) {
                    dispatch(flowsActions.replay(flow))
                }
                break
            }

            case Key.V: {
                if (!shiftKey && flow && flow.modified) {
                    dispatch(flowsActions.revert(flow))
                }
                break
            }

            case Key.X: {
                if (shiftKey) {
                    dispatch(flowsActions.killAll())
                } else if (flow && flow.intercepted) {
                    dispatch(flowsActions.kill(flow))
                }
                break
            }

            case Key.Z: {
                if (!shiftKey) {
                    dispatch(flowsActions.clear())
                }
                break
            }


            default:
                return
        }
    }
}
