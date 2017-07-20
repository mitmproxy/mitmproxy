import reduceOptionsEditor, * as optionsEditorActions from '../../../ducks/ui/optionsEditor'
import { HIDE_MODAL } from '../../../ducks/ui/modal'

describe('optionsEditor reducer', () => {

    it('should return initial state', () => {
        expect(reduceOptionsEditor(undefined, {})).toEqual({})
    })

    let state = undefined
    it('should handle option update start', () => {
        state = reduceOptionsEditor(undefined, optionsEditorActions.startUpdate('foo', 'bar'))
        expect(state).toEqual({ foo: {error: false, isUpdating: true, value: 'bar'}})
    })

    it('should handle option update success', () => {
        expect(reduceOptionsEditor(state, optionsEditorActions.updateSuccess('foo'))).toEqual({foo: undefined})
    })

    it('should handle option update error', () => {
        state = reduceOptionsEditor(state, optionsEditorActions.updateError('foo', 'errorMsg'))
        expect(state).toEqual({ foo: {error: 'errorMsg', isUpdating: false, value: 'bar'}})
        // boolean type
        state = reduceOptionsEditor(undefined, optionsEditorActions.startUpdate('foo', true))
        state = reduceOptionsEditor(state, optionsEditorActions.updateError('foo', 'errorMsg'))
        expect(state).toEqual({ foo: {error: 'errorMsg', isUpdating: false, value: false}})
    })

    it('should handle hide modal', () => {
        expect(reduceOptionsEditor(undefined, {type: HIDE_MODAL})).toEqual({})
    })
})
