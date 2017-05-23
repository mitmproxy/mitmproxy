import React from 'react'
import renderer from 'react-test-renderer'
import FilterDocs from '../../../components/Header/FilterDocs'
import mockFetch from 'jest-fetch-mock'

global.fetch = mockFetch

describe('FilterDocs Component', () => {

    it('should render correctly', () => {
        // fetch successes
        fetch.mockResponseOnce(JSON.stringify({commands: [['cmd1', 'foo'], ['cmd2', 'bar']]}), {status: 200})
        let filterDocs = renderer.create(<FilterDocs/>),
            tree = filterDocs.toJSON()
        // [TODO] doc in render() could not be set correctly.
        console.log(tree)
    })

})
