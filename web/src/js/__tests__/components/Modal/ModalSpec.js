import React from 'react'
import renderer from 'react-test-renderer'
import Modal from '../../../components/Modal/Modal'
import { Provider } from 'react-redux'
import { TStore } from '../../ducks/tutils'

describe('Modal Component', () => {
    let store = TStore()

    it('should render correctly', () => {
        // hide modal by default
        let provider = renderer.create(
            <Provider store={store}>
               <Modal/>
            </Provider>
        ),
            tree = provider.toJSON()
        expect(tree).toMatchSnapshot()

        // option modal show up
        store.getState().ui.modal.activeModal = 'OptionModal'
        provider = renderer.create(
            <Provider store={store}>
                <Modal/>
            </Provider>
        )
        tree = provider.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
