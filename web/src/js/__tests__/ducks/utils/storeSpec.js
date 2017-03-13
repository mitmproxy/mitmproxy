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
        let state = reduceStore(undefined, {})
        expect(state = reduceStore(state, storeActions.add({id: 1}))).toEqual({
                byId: { [1]: {id: 1} },
                listIndex: { [1]: 0 },
                list: [ {id: 1} ],
                view: [ {id: 1} ],
                viewIndex: { 1: 0 },
        })

        expect(reduceStore(state, storeActions.add({id: 9}))).toEqual({
            byId: { [1]: {id:1}, [9]: {id:9} },
            listIndex: { [1]: 0, [9]: 1 },
            list: [ {id: 1}, {id: 9} ],
            view: [ {id: 1}, {id: 9} ],
            viewIndex: { 1: 0, 9: 1 },
        })
    })

    it('should not add the item with duplicated id', () => {
        let state = reduceStore(undefined, storeActions.add({id: 1}))
        expect(reduceStore(state, storeActions.add({id: 1}))).toEqual(state)
    })

    it('should handle update action', () => {
        let state = reduceStore(undefined, storeActions.add({id: 1, foo: "foo"}))
        expect(reduceStore(state, storeActions.update({id:1, foo:"foo1"}))).toEqual({
            byId: { [1]: {id: 1, foo: "foo1"} },
            list: [ {id: 1, foo: "foo1" } ],
            listIndex: { [1]: 0 },
            view: [ {id: 1, foo: "foo1"} ],
            viewIndex: { [1]: 0 },
        })
    })

    it('should handle update action with filter', () => {
        let state = reduceStore(undefined, storeActions.add({id: 0}))
        state = reduceStore(state, storeActions.add({id: 1}))
        expect(reduceStore(state, storeActions.update({id:1},
            item => {return item.id < 1}))).toEqual({
                byId: { [0]: {id: 0}, [1]: {id: 1} },
                list: [ {id: 0}, {id: 1} ],
                listIndex: { [0]: 0, [1]: 1 },
                view: [ {id: 0} ],
                viewIndex: { [0]: 0 }
        })
    })

    it('should handle update action with sort', () => {
        let state = reduceStore(undefined, storeActions.add({id: 2}))
        state = reduceStore(state, storeActions.add({id:3}))
        expect(reduceStore(state, storeActions.update({id: 2}, undefined,
            (a, b) => {return b.id - a.id}))).toEqual({
                // sort by id in descending order
                byId: { [2]: {id: 2}, [3]: {id: 3} },
                list: [ {id: 2}, {id: 3} ],
                listIndex: {[2]: 0, [3]: 1},
                view: [ {id: 3}, {id: 2} ],
                viewIndex: { [2]: 1, [3]: 0 },
        })
    })
})
