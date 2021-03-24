import React from 'react'
import renderer from 'react-test-renderer'
import PureCopyModal from '../../../components/Modal/CopyModal'
import { Provider } from 'react-redux'
import { TStore } from '../../ducks/tutils'

describe('PureCopyModal Component', () => {
    let store = TStore()

    it('should render correctly', () => {
        let pureCopyModal = renderer.create(
            <Provider store={store}>
                <PureCopyModal/>
            </Provider>
        ),
            tree = pureCopyModal.toJSON()
        expect(tree).toMatchSnapshot()
    })

})
