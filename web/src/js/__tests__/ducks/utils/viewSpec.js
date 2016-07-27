jest.unmock('../../../ducks/utils/view')
jest.unmock('lodash')

import reduce, * as view from '../../../ducks/utils/view'
import _ from 'lodash'

describe('view reduce', () => {

    it('should filter items', () => {
        const state = createState([
            { id: 1 },
            { id: 2 }
        ])
        const result = createState([
            { id: 1 }
        ])
        expect(reduce(state, view.updateFilter(state.data, item => item.id === 1))).toEqual(result)
    })

    it('should sort items', () => {
        const state = createState([
            { id: 1 },
            { id: 2 }
        ])
        const result = createState([
            { id: 2 },
            { id: 1 }
        ])
        expect(reduce(state, view.updateSort((a, b) => b.id - a.id))).toEqual(result)
    })

    it('should add item', () => {
        const state = createState([
            { id: 1 },
            { id: 2 }
        ])
        const result = createState([
            { id: 1 },
            { id: 2 },
            { id: 3 }
        ])
        expect(reduce(state, view.add({ id: 3 }))).toEqual(result)
    })

    it('should add item in place', () => {
        const state = createState([
            { id: 1 }
        ])
        const result = createState([
            { id: 3 },
            { id: 1 }
        ])
        expect(reduce(state, view.add({ id: 3 }, undefined, (a, b) => b.id - a.id))).toEqual(result)
    })

    it('should filter added item', () => {
        const state = createState([
            { id: 1 }
        ])
        const result = createState([
            { id: 1 }
        ])
        expect(reduce(state, view.add({ id: 3 }, i => i.id === 1))).toEqual(result)
    })

    it('should update item', () => {
        const state = createState([
            { id: 1, val: 1 },
            { id: 2, val: 2 },
            { id: 3, val: 3 }
        ])
        const result = createState([
            { id: 1, val: 1 },
            { id: 2, val: 3 },
            { id: 3, val: 3 }
        ])
        expect(reduce(state, view.update({ id: 2, val: 3 }))).toEqual(result)
    })

    it('should sort updated item', () => {
        const state = createState([
            { id: 1, val: 1 },
            { id: 2, val: 2 }
        ])
        const result = createState([
            { id: 2, val: 3 },
            { id: 1, val: 1 }
        ])
        expect(reduce(state, view.update({ id: 2, val: 3 }, undefined, (a, b) => b.id - a.id))).toEqual(result)
    })

    it('should filter updated item', () => {
        const state = createState([
            { id: 1, val: 1 },
            { id: 2, val: 2 }
        ])
        const result = createState([
            { id: 1, val: 1 }
        ])
        result.indexOf[2] = null
        expect(reduce(state, view.update({ id: 2, val: 3 }, i => i.id === i.val))).toEqual(result)
    })

    it('should remove item', () => {
        const state = createState([
            { id: 1 },
            { id: 2 }
        ])
        const result = createState([
            { id: 1 }
        ])
        result.indexOf[2] = null
        expect(reduce(state, view.remove(2))).toEqual(result)
    })

    it('should replace items', () => {
        const state = createState([
            { id: 1 },
            { id: 2 }
        ])
        const result = createState([
            { id: 1 }
        ])
        expect(reduce(state, view.receive([{ id: 1 }]))).toEqual(result)
    })

    it('should sort received items', () => {
        const state = createState([
            { id: 1 },
            { id: 2 }
        ])
        const result = createState([
            { id: 2 },
            { id: 1 }
        ])
        expect(reduce(state, view.receive([{ id: 1 }, { id: 2 }], undefined, (a, b) => b.id - a.id))).toEqual(result)
    })

    it('should filter received', () => {
        const state = createState([
            { id: 1 },
            { id: 2 }
        ])
        const result = createState([
            { id: 1 }
        ])
        expect(reduce(state, view.receive([{ id: 1 }, { id: 2 }], i => i.id === 1))).toEqual(result)
    })
})

function createState(items) {
    return {
        data: items,
        indexOf: _.fromPairs(items.map((item, index) => [item.id, index]))
    }
}
