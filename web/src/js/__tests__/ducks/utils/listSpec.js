jest.unmock('lodash')
jest.unmock('../../../ducks/utils/list')

import reduce, * as list from '../../../ducks/utils/list'
import _ from 'lodash'

describe('list reduce', () => {

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
        expect(reduce(state, list.add({ id: 3 }))).toEqual(result)
    })

    it('should update item', () => {
        const state = createState([
            { id: 1, val: 1 },
            { id: 2, val: 2 }
        ])
        const result = createState([
            { id: 1, val: 1 },
            { id: 2, val: 3 }
        ])
        expect(reduce(state, list.update({ id: 2, val: 3 }))).toEqual(result)
    })

    it('should remove item', () => {
        const state = createState([
            { id: 1 },
            { id: 2 }
        ])
        const result = createState([
            { id: 1 }
        ])
        result.byId[2] = result.indexOf[2] = null
        expect(reduce(state, list.remove(2))).toEqual(result)
    })

    it('should replace all items', () => {
        const state = createState([
            { id: 1 },
            { id: 2 }
        ])
        const result = createState([
            { id: 1 }
        ])
        expect(reduce(state, list.receive([{ id: 1 }]))).toEqual(result)
    })
})

function createState(items) {
    return {
        data: items,
        byId: _.fromPairs(items.map((item, index) => [item.id, item])),
        indexOf: _.fromPairs(items.map((item, index) => [item.id, index]))
    }
}
