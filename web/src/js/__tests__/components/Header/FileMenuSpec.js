import React from 'react'
import renderer from 'react-test-renderer'
import { FileMenu } from '../../../components/Header/FileMenu'

global.confirm = jest.fn( s => true )

describe('FileMenu Component', () => {
    let clearFn = jest.fn(),
        loadFn = jest.fn(),
        saveFn = jest.fn(),
        openModalFn = jest.fn(),
        mockEvent = {
            preventDefault: jest.fn(),
            target: { files: ["foo", "bar "] }
        },
        createNodeMock = () => { return { click: jest.fn() }},
        fileMenu = renderer.create(
            <FileMenu
                clearFlows={clearFn}
                loadFlows={loadFn}
                saveFlows={saveFn}
                openModal={openModalFn}
            />,
            { createNodeMock }),
        tree = fileMenu.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    let ul = tree.children[1]

    it('should clear flows', () => {
        let a = ul.children[0].children[1]
        a.props.onClick(mockEvent)
        expect(mockEvent.preventDefault).toBeCalled()
        expect(clearFn).toBeCalled()
    })

    it('should load flows', () => {
        let fileChooser = ul.children[1].children[1],
            input = fileChooser.children[2]
        input.props.onChange(mockEvent)
        expect(loadFn).toBeCalledWith("foo")
    })

    it('should save flows', () => {
        let a = ul.children[2].children[1]
        a.props.onClick(mockEvent)
        expect(saveFn).toBeCalled()
    })
})
