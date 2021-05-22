jest.mock('../../utils')

import reduceFlows from "../../ducks/flows"
import * as flowActions from "../../ducks/flows"
import reduceStore from "../../ducks/utils/store"
import { fetchApi } from "../../utils"
import { createStore } from "./tutils"

describe('flow reducer', () => {
    let state = undefined
    for (let i of [1, 2, 3, 4]) {
        state = reduceFlows(state, { type: flowActions.ADD, data: { id: i }, cmd: 'add' })
    }

    it('should return initial state', () => {
        expect(reduceFlows(undefined, {})).toEqual({
            highlight: null,
            filter: null,
            sort: { column: null, desc: false },
            selected: [],
            ...reduceStore(undefined, {})
        })
    })

    describe('selections', () => {
        it('should be possible to select a single flow', () => {
            expect(reduceFlows(state, flowActions.select(2))).toEqual(
                {
                    ...state,
                    selected: [2],
                }
            )
        })

        it('should be possible to deselect a flow', () => {
            expect(reduceFlows({ ...state, selected: [1] }, flowActions.select())).toEqual(
                {
                    ...state,
                    selected: [],
                }
            )
        })

        it('should be possible to select relative', () => {
            // haven't selected any flow
            expect(
                flowActions.selectRelative(state, 1)
            ).toEqual(
                flowActions.select(4)
            )

            // already selected some flows
            expect(
                flowActions.selectRelative({ ...state, selected: [2] }, 1)
            ).toEqual(
                flowActions.select(3)
            )
        })

        it('should update state.selected on remove', () => {
            let next
            next = reduceFlows({ ...state, selected: [2] }, {
                type: flowActions.REMOVE,
                data: 2,
                cmd: 'remove'
            })
            expect(next.selected).toEqual([3])

            //last row
            next = reduceFlows({ ...state, selected: [4] }, {
                type: flowActions.REMOVE,
                data: 4,
                cmd: 'remove'
            })
            expect(next.selected).toEqual([3])

            //multiple selection
            next = reduceFlows({ ...state, selected: [2, 3, 4] }, {
                type: flowActions.REMOVE,
                data: 3,
                cmd: 'remove'
            })
            expect(next.selected).toEqual([2, 4])
        })
    })

    it('should be possible to set filter', () => {
        let filt = "~u 123"
        expect(reduceFlows(undefined, flowActions.setFilter(filt)).filter).toEqual(filt)
    })

    it('should be possible to set highlight', () => {
        let key = "foo"
        expect(reduceFlows(undefined, flowActions.setHighlight(key)).highlight).toEqual(key)
    })

    it('should be possible to set sort', () => {
        let sort = { column: "TLSColumn", desc: 1 }
        expect(reduceFlows(undefined, flowActions.setSort(sort.column, sort.desc)).sort).toEqual(sort)
    })

})

describe('flows actions', () => {

    let store = createStore({ reduceFlows })

    let tflow = { id: 1 }
    it('should handle resume action', () => {
        store.dispatch(flowActions.resume(tflow))
        expect(fetchApi).toBeCalledWith('/flows/1/resume', { method: 'POST' })
    })

    it('should handle resumeAll action', () => {
        store.dispatch(flowActions.resumeAll())
        expect(fetchApi).toBeCalledWith('/flows/resume', { method: 'POST' })
    })

    it('should handle kill action', () => {
        store.dispatch(flowActions.kill(tflow))
        expect(fetchApi).toBeCalledWith('/flows/1/kill', { method: 'POST' })

    })

    it('should handle killAll action', () => {
        store.dispatch(flowActions.killAll())
        expect(fetchApi).toBeCalledWith('/flows/kill', { method: 'POST' })
    })

    it('should handle remove action', () => {
        store.dispatch(flowActions.remove(tflow))
        expect(fetchApi).toBeCalledWith('/flows/1', { method: 'DELETE' })
    })

    it('should handle duplicate action', () => {
        store.dispatch(flowActions.duplicate(tflow))
        expect(fetchApi).toBeCalledWith('/flows/1/duplicate', { method: 'POST' })
    })

    it('should handle replay action', () => {
        store.dispatch(flowActions.replay(tflow))
        expect(fetchApi).toBeCalledWith('/flows/1/replay', { method: 'POST' })
    })

    it('should handle revert action', () => {
        store.dispatch(flowActions.revert(tflow))
        expect(fetchApi).toBeCalledWith('/flows/1/revert', { method: 'POST' })
    })

    it('should handle update action', () => {
        store.dispatch(flowActions.update(tflow, 'foo'))
        expect(fetchApi.put).toBeCalledWith('/flows/1', 'foo')
    })

    it('should handle uploadContent action', () => {
        let body = new FormData(),
        file     = new window.Blob(['foo'], { type: 'plain/text' })
        body.append('file', file)
        store.dispatch(flowActions.uploadContent(tflow, 'foo', 'foo'))
        // window.Blob's lastModified is always the current time,
        // which causes flaky tests on comparison.
        expect(fetchApi).toBeCalledWith('/flows/1/foo/content.data', { method: 'POST', body: expect.anything()})
    })

    it('should handle clear action', () => {
        store.dispatch(flowActions.clear())
        expect(fetchApi).toBeCalledWith('/clear', { method: 'POST'} )
    })

    it('should handle download action', () => {
        let state = reduceFlows(undefined, {})
        expect(reduceFlows(state, flowActions.download())).toEqual(state)
    })

    it('should handle upload action', () => {
        let body = new FormData()
        body.append('file', 'foo')
        store.dispatch(flowActions.upload('foo'))
        expect(fetchApi).toBeCalledWith('/flows/dump', { method: 'POST', body })
    })
})

describe('makeSort', () => {
    it('should be possible to sort by TLSColumn', () => {
        let sort = flowActions.makeSort({ column: 'TLSColumn', desc: true }),
            a    = { request: { scheme: 'http' } },
            b    = { request: { scheme: 'https' } }
        expect(sort(a, b)).toEqual(1)
    })

    it('should be possible to sort by PathColumn', () => {
        let sort = flowActions.makeSort({ column: 'PathColumn', desc: true }),
            a    = { request: {} },
            b    = { request: {} }
        expect(sort(a, b)).toEqual(0)

    })

    it('should be possible to sort by MethodColumn', () => {
        let sort = flowActions.makeSort({ column: 'MethodColumn', desc: true }),
            a    = { request: { method: 'GET' } },
            b    = { request: { method: 'POST' } }
        expect(sort(b, a)).toEqual(-1)
    })

    it('should be possible to sort by StatusColumn', () => {
        let sort = flowActions.makeSort({ column: 'StatusColumn', desc: false }),
            a    = { response: { status_code: 200 } },
            b    = { response: { status_code: 404 } }
        expect(sort(a, b)).toEqual(-1)
    })

    it('should be possible to sort by TimeColumn', () => {
        let sort = flowActions.makeSort({ column: 'TimeColumn', desc: false }),
            a    = { response: { timestamp_end: 9 }, request: { timestamp_start: 8 } },
            b    = { response: { timestamp_end: 10 }, request: { timestamp_start: 8 } }
        expect(sort(b, a)).toEqual(1)
    })

    it('should be possible to sort by SizeColumn', () => {
        let sort = flowActions.makeSort({ column: 'SizeColumn', desc: true }),
            a    = { request: { contentLength: 1 }, response: { contentLength: 1 } },
            b    = { request: { contentLength: 1 } }
        expect(sort(a, b)).toEqual(-1)
    })
})
