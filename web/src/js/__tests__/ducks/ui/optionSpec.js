import reduceOption, * as optionActions from '../../../ducks/ui/option'

describe('option reducer', () => {

    it('should return the initial state', () => {
        expect(reduceOption(undefined, {})).toEqual({})
    })

    let state = undefined
    it('should handle option update start', () => {
        state = reduceOption(undefined, {
            type: optionActions.OPTION_UPDATE_START, option: 'foo', value: 'bar'
        })
        expect(state).toEqual({
            foo: {
                error: false,
                isUpdating: true,
                value: 'bar'
            }
        })
    })

    it('should handle option update success', () => {
        expect(reduceOption(state, {
            type: optionActions.OPTION_UPDATE_SUCCESS, option: 'foo'
        })).toEqual({})
    })

    it('should handle option update error', () => {
        expect(reduceOption(undefined, {
            type: optionActions.OPTION_UPDATE_ERROR, option: 'foo', error: 'errorMsg'
        })).toEqual({
            foo: {
                error: 'errorMsg',
                isUpdating: false,
            }
        })
    })
})
