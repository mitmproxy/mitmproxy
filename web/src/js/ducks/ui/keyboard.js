import { Key } from '../../utils'
import { selectRelative as selectFlowRelative } from '../flowView'
import { selectTab } from './flow'
import * as flowsActions from '../flows'

export function onKeyDown(e) {
    e.preventDefault()

    if (e.ctrlKey) {
        return () => {}
    }

    const shiftKey = e.shiftKey

    return (dispatch, getState) => {

        const flow = getState().flows.byId[getState().flows.selected[0]]

        switch (e.keyCode) {
            case Key.K:
            case Key.UP:
                dispatch(selectFlowRelative(-1))
                break

            case Key.J:
            case Key.DOWN:
                dispatch(selectFlowRelative(+1))
                break

            case Key.SPACE:
            case Key.PAGE_DOWN:
                dispatch(selectFlowRelative(+10))
                break

            case Key.PAGE_UP:
                dispatch(selectFlowRelative(-10))
                break

            case Key.END:
                dispatch(selectFlowRelative(+1e10))
                break

            case Key.HOME:
                dispatch(selectFlowRelative(-1e10))
                break

            case Key.ESC:
                dispatch(flowsActions.select(null))
                break

            case Key.LEFT:
            {
                if(!flow) break
                let tabs       = ['request', 'response', 'error'].filter(k => flow[k]).concat(['details']),
                    currentTab = getState().ui.flow.tab,
                    nextTab    = tabs[(tabs.indexOf(currentTab) - 1 + tabs.length) % tabs.length]
                dispatch(selectTab(nextTab))
                break
            }

            case Key.TAB:
            case Key.RIGHT:
            {
                if(!flow) break
                let tabs       = ['request', 'response', 'error'].filter(k => flow[k]).concat(['details']),
                    currentTab = getState().ui.flow.tab,
                    nextTab    = tabs[(tabs.indexOf(currentTab) + 1) % tabs.length]
                dispatch(selectTab(nextTab))
                break
            }

            case Key.C:
                if (shiftKey) {
                    dispatch(flowsActions.clear())
                }
                break

            case Key.D:
            {
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

            case Key.A:
            {
                if (shiftKey) {
                    dispatch(flowsActions.acceptAll())
                } else if (flow && flow.intercepted) {
                    dispatch(flowsActions.accept(flow))
                }
                break
            }

            case Key.R:
            {
                if (!shiftKey && flow) {
                    dispatch(flowsActions.replay(flow))
                }
                break
            }

            case Key.V:
            {
                if (!shiftKey && flow && flow.modified) {
                    dispatch(flowsActions.revert(flow))
                }
                break
            }

            default:
                return
        }
    }
}
