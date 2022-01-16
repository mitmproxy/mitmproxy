import reduceFlows, * as flowsActions from "../../../ducks/flows";
import {onKeyDown} from '../../../ducks/ui/keyboard'
import * as UIActions from '../../../ducks/ui/flow'
import * as modalActions from '../../../ducks/ui/modal'
import {fetchApi, runCommand} from '../../../utils'
import {TStore} from "../tutils";

jest.mock('../../../utils')

describe('onKeyDown', () => {
    let flows = flowsActions.defaultState;
    for (let i = 1; i <= 12; i++) {
        flows = reduceFlows(flows, {
            type: flowsActions.ADD,
            data: {id: i + "", request: true, response: true, type: "http"},
            cmd: 'add'
        })
    }

    const store = TStore();
    store.getState().flows = flows;

    let createKeyEvent = (key, ctrlKey = false) => {
        // @ts-ignore
        return onKeyDown({key, ctrlKey, preventDefault: jest.fn()})
    }

    afterEach(() => {
        store.clearActions()
        // @ts-ignore
        fetchApi.mockClear()
    });

    it('should handle cursor up', () => {
        store.getState().flows = reduceFlows(flows, flowsActions.select("2"))
        store.dispatch(createKeyEvent("k"))
        expect(store.getActions()).toEqual([{flowIds: ["1"], type: flowsActions.SELECT}])

        store.clearActions()
        store.dispatch(createKeyEvent("ArrowUp"))
        expect(store.getActions()).toEqual([{flowIds: ["1"], type: flowsActions.SELECT}])
    })

    it('should handle cursor down', () => {
        store.dispatch(createKeyEvent("j"))
        expect(store.getActions()).toEqual([{flowIds: ["3"], type: flowsActions.SELECT}])

        store.clearActions()
        store.dispatch(createKeyEvent("ArrowDown"))
        expect(store.getActions()).toEqual([{flowIds: ["3"], type: flowsActions.SELECT}])
    })

    it('should handle page down', () => {
        store.dispatch(createKeyEvent(" "))
        expect(store.getActions()).toEqual([{flowIds: ["12"], type: flowsActions.SELECT}])

        store.getState().flows = reduceFlows(flows, flowsActions.select("1"))
        store.clearActions()
        store.dispatch(createKeyEvent("PageDown"))
        expect(store.getActions()).toEqual([{flowIds: ["11"], type: flowsActions.SELECT}])
    })

    it('should handle page up', () => {
        store.getState().flows = reduceFlows(flows, flowsActions.select("11"))
        store.dispatch(createKeyEvent("PageUp"))
        expect(store.getActions()).toEqual([{flowIds: ["1"], type: flowsActions.SELECT}])
    })

    it('should handle select first', () => {
        store.dispatch(createKeyEvent("Home"))
        expect(store.getActions()).toEqual([{flowIds: ["1"], type: flowsActions.SELECT}])
    })

    it('should handle select last', () => {
        store.getState().flows = reduceFlows(flows, flowsActions.select("1"))
        store.dispatch(createKeyEvent("End"))
        expect(store.getActions()).toEqual([{flowIds: ["12"], type: flowsActions.SELECT}])
    })

    it('should handle deselect', () => {
        store.dispatch(createKeyEvent("Escape"))
        expect(store.getActions()).toEqual([{flowIds: [], type: flowsActions.SELECT}])
    })

    it('should handle switch to left tab', () => {
        store.dispatch(createKeyEvent("ArrowLeft"))
        expect(store.getActions()).toEqual([{tab: 'timing', type: UIActions.SET_TAB}])
    })

    it('should handle switch to right tab', () => {
        store.dispatch(createKeyEvent("Tab"))
        expect(store.getActions()).toEqual([{tab: 'response', type: UIActions.SET_TAB}])

        store.clearActions()
        store.dispatch(createKeyEvent("ArrowRight"))
        expect(store.getActions()).toEqual([{tab: 'response', type: UIActions.SET_TAB}])
    })

    it('should handle delete action', () => {
        store.dispatch(createKeyEvent("d"))
        expect(fetchApi).toBeCalledWith('/flows/1', {method: 'DELETE'})

    })

    it('should handle create action', () => {
        store.dispatch(createKeyEvent("n"))
        expect(runCommand).toBeCalledWith('view.flows.create', "get", "https://example.com/")
    })

    it('should handle duplicate action', () => {
        store.dispatch(createKeyEvent("D"))
        expect(fetchApi).toBeCalledWith('/flows/1/duplicate', {method: 'POST'})
    })

    it('should handle resume action', () => {
        // resume all
        store.dispatch(createKeyEvent("A"))
        expect(fetchApi).toBeCalledWith('/flows/resume', {method: 'POST'})
        // resume
        store.getState().flows.byId[store.getState().flows.selected[0]].intercepted = true
        store.dispatch(createKeyEvent("a"))
        expect(fetchApi).toBeCalledWith('/flows/1/resume', {method: 'POST'})
    })

    it('should handle replay action', () => {
        store.dispatch(createKeyEvent("r"))
        expect(fetchApi).toBeCalledWith('/flows/1/replay', {method: 'POST'})
    })

    it('should handle revert action', () => {
        store.getState().flows.byId[store.getState().flows.selected[0]].modified = true
        store.dispatch(createKeyEvent("v"))
        expect(fetchApi).toBeCalledWith('/flows/1/revert', {method: 'POST'})
    })

    it('should handle kill action', () => {
        // kill all
        store.dispatch(createKeyEvent("X"))
        expect(fetchApi).toBeCalledWith('/flows/kill', {method: 'POST'})
        // kill
        store.dispatch(createKeyEvent("x"))
        expect(fetchApi).toBeCalledWith('/flows/1/kill', {method: 'POST'})
    })

    it('should handle clear action', () => {
        store.dispatch(createKeyEvent("z"))
        expect(fetchApi).toBeCalledWith('/clear', {method: 'POST'})
    })

    it('should stop on some action with no flow is selected', () => {
        store.getState().flows = reduceFlows(undefined, {})
        store.dispatch(createKeyEvent("ArrowLeft"))
        store.dispatch(createKeyEvent("Tab"))
        store.dispatch(createKeyEvent("ArrowRight"))
        store.dispatch(createKeyEvent("D"))
        expect(fetchApi).not.toBeCalled()
    })

    it('should do nothing when Ctrl and undefined key is pressed ', () => {
        store.dispatch(createKeyEvent("Backspace", true))
        store.dispatch(createKeyEvent(0))
        expect(fetchApi).not.toBeCalled()
    })

    it('should close modal', () => {
        store.getState().ui.modal.activeModal = true
        store.dispatch(createKeyEvent("Escape"))
        expect(store.getActions()).toEqual([{type: modalActions.HIDE_MODAL}])
    })

})
