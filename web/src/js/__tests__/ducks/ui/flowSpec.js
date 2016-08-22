jest.unmock('../../../ducks/ui/flow')
jest.unmock('../../../ducks/flows')
jest.unmock('lodash')

import _ from 'lodash'
import reducer, {
                    startEdit,
                    setContentViewDescription,
                    setShowFullContent,
                    setContent,
                    updateEdit
                } from '../../../ducks/ui/flow'

import { select, updateFlow } from '../../../ducks/flows'

describe('flow reducer', () => {
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
        expect(reducer({contentView: 'foo'}, select(1)).contentView).toEqual('foo')
    })

    it('should change the contentview mode to auto after editing when a new flow will be selected', () => {
        expect(reducer({contentView: 'foo', modifiedFlow : 'test_flow'}, select(1)).contentView).toEqual('Auto')
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
        expect(reducer({modifiedFlow}, updateFlow(updatedFlow)).modifiedFlow).toEqual(modifiedFlow)
    })

     it('should stop editing when the selected flow is updated', () => {
        let modifiedFlow = {id: 1}
        let updatedFlow = {id: 1}
        expect(reducer({modifiedFlow}, updateFlow(updatedFlow)).modifiedFlow).toBeFalsy()
    })
})
