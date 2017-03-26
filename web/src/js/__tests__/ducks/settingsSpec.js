jest.unmock('../../ducks/settings')
jest.mock('../../utils')

import reduceSettings from '../../ducks/settings'
import * as SettingsActions from '../../ducks/settings'

describe('setting reducer', () => {
    it('should return initial state', () => {
        expect(reduceSettings(undefined, {})).toEqual({})
    })

    it('should handle receive action', () => {
        let action = { type: SettingsActions.RECEIVE, data: 'foo' }
        expect(reduceSettings(undefined, action)).toEqual('foo')
    })

    it('should handle update action', () => {
        let action = {type: SettingsActions.UPDATE, data: {id: 1} }
        expect(reduceSettings(undefined, action)).toEqual({id: 1})

        expect(reduceSettings(undefined, SettingsActions.update())).toEqual({})
    })
})
