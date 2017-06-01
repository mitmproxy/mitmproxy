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

        expect(state = reduceStore(state, storeActions.add(b))).toEqual({
            byId: { 1: a, 9: b },
            listIndex: { 1: 0, 9: 1 },
            list: [ a, b ],
            view: [ a, b ],
            viewIndex: { 1: 0, 9: 1 },
        })

        // add item and sort them
        let c = {id: 0}
        expect(reduceStore(state, storeActions.add(c, undefined,
            (a, b) => {return a.id - b.id}))).toEqual({
                byId: {...state.byId, 0: c },
                list: [...state.list, c ],
                listIndex: {...state.listIndex, 0:2},
                view: [c, ...state.view ],
                viewIndex: {0: 0, 1: 1, 9: 2}

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
        let a = {id: 0}, b = {id: 1},
            state = reduceStore(undefined, storeActions.receive([a, b]))
        state = reduceStore(state, storeActions.update(b,
            item => {return item.id != 1}))
        expect(state).toEqual({
                byId: { 0: a, 1: b },
                list: [ a, b ],
                listIndex: { 0: 0, 1: 1 },
                view: [ a ],
                viewIndex: { 0: 0 }
        })
        expect(reduceStore(state, storeActions.update(b,
            item => {return item.id != 0}))).toEqual({
                byId: { 0: a, 1: b },
                list: [ a, b ],
                listIndex: { 0: 0, 1: 1 },
                view: [ a, b ],
                viewIndex: { 0: 0, 1: 1 }
        })
    })

    it('should handle update action with sort', () => {
        let a = {id: 2},
            b = {id: 3},
            state = reduceStore(undefined, storeActions.receive([a, b]))
        expect(reduceStore(state, storeActions.update(b, undefined,
            (a, b) => {return b.id - a.id}))).toEqual({
                // sort by id in descending order
                byId: { 2: a, 3: b },
                list: [ a, b ],
                listIndex: {2: 0, 3: 1},
                view: [ b, a ],
                viewIndex: { 2: 1, 3: 0 },
        })

        let state1 = reduceStore(undefined, storeActions.receive([b, a]))
        expect(reduceStore(state1, storeActions.update(b, undefined,
            (a, b) => {return a.id - b.id}))).toEqual({
                // sort by id in ascending order
                byId: { 2: a, 3: b },
                list: [ b, a ],
                listIndex: {2: 1, 3: 0},
                view: [ a, b ],
                viewIndex: { 2: 0, 3: 1 },
        })
    })

    it('should set filter', () => {
        let a = { id: 1 },
            b = { id: 2 },
            state = reduceStore(undefined, storeActions.receive([a, b]))
        expect(reduceStore(state, storeActions.setFilter(
            item => {return item.id != 1}
        ))).toEqual({
            byId: { 1 :a, 2: b },
            list: [ a, b ],
            listIndex:{ 1: 0, 2: 1},
            view: [ b ],
            viewIndex: { 2: 0 },
        })
    })

    it('should set sort', () => {
        let a = { id: 1 },
            b = { id: 2 },
            state = reduceStore(undefined, storeActions.receive([a, b]))
        expect(reduceStore(state, storeActions.setSort(
            (a, b) => { return b.id - a.id }
        ))).toEqual({
            byId: { 1: a, 2: b },
            list: [ a, b ],
            listIndex: {1: 0, 2: 1},
            view: [ b, a ],
            viewIndex: { 1: 1, 2: 0 },
        })
    })

    it('should handle remove action', () => {
        let a = { id: 1 }, b = { id: 2},
            state = reduceStore(undefined, storeActions.receive([a, b]))
        expect(reduceStore(state, storeActions.remove(1))).toEqual({
            byId: { 2: b },
            list: [ b ],
            listIndex: { 2: 0 },
            view: [ b ],
            viewIndex: { 2: 0 },
        })

        expect(reduceStore(state, storeActions.remove(3))).toEqual(state)
    })

    it('should handle receive list', () => {
        let a = { id: 1 }, b = { id: 2 },
            list = [ a, b ]
        expect(reduceStore(undefined, storeActions.receive(list))).toEqual({
            byId: { 1: a, 2: b },
            list: [ a, b ],
            listIndex: {1: 0, 2: 1},
            view: [ a, b ],
            viewIndex: { 1: 0, 2: 1 },
        })
    })
})
