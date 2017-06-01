import React from 'react'
import EventLogList from '../../../components/EventLog/EventList'
import TestUtils from 'react-dom/test-utils'

describe('EventList Component', () => {
     let mockEventList = [
            { id: 1, level: 'info', message: 'foo' },
            { id: 2, level: 'error', message: 'bar' }
        ],
            eventLogList = TestUtils.renderIntoDocument(<EventLogList events={mockEventList}/>)

    it('should render correctly', () => {
        expect(eventLogList.state).toMatchSnapshot()
        expect(eventLogList.props).toMatchSnapshot()
    })

    it('should handle componentWillUnmount', () => {
        window.removeEventListener = jest.fn()
        eventLogList.componentWillUnmount()
        expect(window.removeEventListener).toBeCalledWith('resize', eventLogList.onViewportUpdate)
    })
})
