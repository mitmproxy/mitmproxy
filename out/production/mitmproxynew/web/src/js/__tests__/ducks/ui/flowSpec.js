import _ from 'lodash'
import reducer, {
                    startEdit,
                    setContentViewDescription,
                    setShowFullContent,
                    setContent,
                    updateEdit,
                    stopEdit,
                    setContentView,
                    selectTab,
                    displayLarge
                } from '../../../ducks/ui/flow'

import * as flowActions from '../../../ducks/flows'

describe('flow reducer', () => {
    it('should return initial state', () => {
        expect(reducer(undefined, {})).toEqual({
            displayLarge: false,
            viewDescription: '',
            showFullContent: false,
            modifiedFlow: false,
            contentView: 'Auto',
            tab: 'request',
            content: [],
            maxContentLines: 80,
        })
    })

    it('should change to edit mode', () => {
        let testFlow = {flow : 'foo'}
        const newState = reducer(undefined, startEdit({ flow: 'foo' }))
        expect(newState.contentView).toEqual('Edit')
        expect(newState.modifiedFlow).toEqual(testFlow)
        expect(newState.showFullContent).toEqual(true)
    })
    it('should set the view description', () => {
        expect(reducer(undefined, setContentViewDescription('description')).viewDescription)
            .toEqual('description')
    })

    it('should set show full content', () => {
        expect(reducer({showFullContent: false}, setShowFullContent()).showFullContent)
            .toBeTruthy()
    })

    it('should set showFullContent to true', () => {
        let maxLines = 10
        let content = _.range(maxLines)
        const newState = reducer({maxContentLines: maxLines}, setContent(content) )
        expect(newState.showFullContent).toBeTruthy()
        expect(newState.content).toEqual(content)
    })

    it('should set showFullContent to false', () => {
        let maxLines = 5
        let content = _.range(maxLines+1);
        const newState = reducer({maxContentLines: maxLines}, setContent(_.range(maxLines+1)))
        expect(newState.showFullContent).toBeFalsy()
        expect(newState.content).toEqual(content)
    })

    it('should not change the contentview mode', () => {
        expect(reducer({contentView: 'foo'}, flowActions.select(1)).contentView).toEqual('foo')
    })

    it('should change the contentview mode to auto after editing when a new flow will be selected', () => {
        expect(reducer({contentView: 'foo', modifiedFlow : 'test_flow'}, flowActions.select(1)).contentView).toEqual('Auto')
    })

    it('should set update and merge the modifiedflow with the update values', () => {
        let modifiedFlow = {headers: []}
        let updateValues = {content: 'bar'}
        let result = {headers: [], content: 'bar'}
        expect(reducer({modifiedFlow}, updateEdit(updateValues)).modifiedFlow).toEqual(result)
    })

    it('should not change the state when a flow is updated which is not selected', () => {
        let modifiedFlow = {id: 1}
        let updatedFlow = {id: 0}
        expect(reducer({modifiedFlow}, stopEdit(updatedFlow, modifiedFlow)).modifiedFlow).toEqual(modifiedFlow)
    })

    it('should stop editing when the selected flow is updated', () => {
        let modifiedFlow = {id: 1}
        let updatedFlow = {id: 1}
        expect(reducer(
            { modifiedFlow },
            {type: flowActions.UPDATE, data: modifiedFlow}
            ).modifiedFlow
        ).toBeFalsy()
    })

    it('should set content view', () => {
        let state = reducer(undefined, setContentView('Edit'))
        expect(state.contentView).toEqual('Edit')
        expect(state.showFullContent).toBeTruthy()
    })

    it('should select different tabs', () => {
        let state = reducer(undefined, selectTab('response'))
        expect(state.tab).toEqual('response')
        expect(state.displayLarge).toBeFalsy()
        expect(state.showFullContent).toBeFalsy()
    })

    it('should display large', () => {
        expect(reducer(undefined, displayLarge()).displayLarge).toBeTruthy()
    })
})
