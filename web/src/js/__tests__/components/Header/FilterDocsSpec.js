import React from 'react'
import renderer from 'react-test-renderer'
import FilterDocs from '../../../components/Header/FilterDocs'

describe('FilterDocs Component', () => {
    let mockResponse = { json:
            jest.fn(() => { return { commands: [['cmd1', 'foo'], ['cmd2', 'bar']]}})
        },
        promise = Promise.resolve(mockResponse)
    global.fetch = jest.fn(r => { return promise })

    let filterDocs = renderer.create(<FilterDocs/>),
        tree = filterDocs.toJSON()

    it('should render correctly when fetch success', () => {
        expect(tree).toMatchSnapshot()
    })
})
