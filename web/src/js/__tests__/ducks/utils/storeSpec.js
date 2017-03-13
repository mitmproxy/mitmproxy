jest.unmock('../../../ducks/utils/store')

import reduceStore, * as storeActions from '../../../ducks/utils/store'

describe('store reducer', () => {
    it('should return initial state', () => {
        expect(reduceStore(undefined, {})).toEqual({
            byId: {},
            list: [],
            listIndex: {},
            view: [],
            viewIndex: {},
        })
    })

    it('should handle add action', () => {
        let a = {id: 1},
            b = {id: 9},
            state = reduceStore(undefined, {})
        expect(state = reduceStore(state, storeActions.add(a))).toEqual({
                byId: { 1: a },
                listIndex: { 1: 0 },
                list: [ a ],
                view: [ a ],
                viewIndex: { 1: 0 },
        })

        expect(reduceStore(state, storeActions.add(b))).toEqual({
            byId: { 1: a, 9: b },
            listIndex: { 1: 0, 9: 1 },
            list: [ a, b ],
            view: [ a, b ],
            viewIndex: { 1: 0, 9: 1 },
        })
    })

    it('should not add the item with duplicated id', () => {
        let a = {id: 1},
            state = reduceStore(undefined, storeActions.add(a))
        expect(reduceStore(state, storeActions.add(a))).toEqual(state)
    })

    it('should handle update action', () => {
        let a = {id: 1, foo: "foo"},
            updated = {...a, foo: "bar"},
            state = reduceStore(undefined, storeActions.add(a))
        expect(reduceStore(state, storeActions.update(updated))).toEqual({
            byId: { 1: updated },
            list: [ updated ],
            listIndex: { 1: 0 },
            view: [ updated ],
            viewIndex: { 1: 0 },
        })
    })

    it('should handle update action with filter', () => {
        let a = {id: 0},
            b = {id: 1},
            state = reduceStore(undefined, storeActions.add(a))
        state = reduceStore(state, storeActions.add(b))
        expect(reduceStore(state, storeActions.update(b,
            item => {return item.id < 1}))).toEqual({
                byId: { 0: a, 1: b },
                list: [ a, b ],
                listIndex: { 0: 0, 1: 1 },
                view: [ a ],
                viewIndex: { 0: 0 }
        })
    })

    it('should handle update action with sort', () => {
        let a = {id: 2},
            b = {id: 3},
            state = reduceStore(undefined, storeActions.add(a))
        state = reduceStore(state, storeActions.add(b))
        expect(reduceStore(state, storeActions.update(a, undefined,
            (a, b) => {return b.id - a.id}))).toEqual({
                // sort by id in descending order
                byId: { 2: a, 3: b },
                list: [ a, b ],
                listIndex: {2: 0, 3: 1},
                view: [ b, a ],
                viewIndex: { 2: 1, 3: 0 },
        })
    })
})
