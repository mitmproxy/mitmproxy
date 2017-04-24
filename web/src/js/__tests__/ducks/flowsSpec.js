jest.unmock('../../ducks/flows');
jest.mock('../../utils')

import reduceFlows from "../../ducks/flows"
import * as flowActions from "../../ducks/flows"
import reduceStore from "../../ducks/utils/store"
import {fetchApi} from "../../utils"
import {createStore} from "./tutils"

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

    let store = createStore({reduceFlows})

    let tflow = { id: 1 }
    it('should handle resume action', () => {
        store.dispatch(flowActions.resume(tflow))
        expect(fetchApi).toBeCalledWith('/flows/1/resume', { method: 'POST' })
    })

    it('should handle resumeAll action', () => {
        flowActions.resumeAll()()
    })

    it('should handle kill action', () => {
        flowActions.kill(tflow)()
    })

    it('should handle killAll action', () => {
        flowActions.killAll()()
    })

    it('should handle remove action', () => {
        flowActions.remove(tflow)()
    })

    it('should handle duplicate action', () => {
        flowActions.duplicate(tflow)()
    })

    it('should handle replay action', () => {
        flowActions.replay(tflow)()
    })

    it('should handle revert action', () => {
        flowActions.revert(tflow)()
    })

    it('should handle update action', () => {
        flowActions.update(tflow, "foo")()
    })

    it('should handle updateContent action', () => {
        flowActions.uploadContent(tflow, "foo", "foo")()
    })

    it('should handle clear action', () => {
        flowActions.clear()()
    })

    it('should handle download action', () => {
        let state = reduceFlows(undefined, {})
        expect(reduceFlows(state, flowActions.download())).toEqual(state)
    })

    it('should handle upload action', () => {
        flowActions.upload("foo")()
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
