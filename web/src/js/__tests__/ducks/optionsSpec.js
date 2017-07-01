jest.mock('../../utils')

import reduceOptions, * as OptionsActions from '../../ducks/options'

describe('option reducer', () => {
    it('should return initial state', () => {
        expect(reduceOptions(undefined, {})).toEqual({})
    })

    it('should handle receive action', () => {
        let action = { type: OptionsActions.RECEIVE, data: 'foo' }
        expect(reduceOptions(undefined, action)).toEqual('foo')
    })

    it('should handle update action', () => {
        let action = {type: OptionsActions.UPDATE, data: {id: 1} }
        expect(reduceOptions(undefined, action)).toEqual({id: 1})
    })
})

describe('option actions', () => {
    it('should be possible to update option', () => {
        expect(reduceOptions(undefined, OptionsActions.update())).toEqual({})
    })
})
