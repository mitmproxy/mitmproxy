import React from 'react'
import renderer from 'react-test-renderer'
import { Options, ChoicesOption } from '../../../components/Modal/Option'

describe('BooleanOption Component', () => {
    let BooleanOption = Options['bool'],
        onChangeFn = jest.fn(),
        booleanOption = renderer.create(
            <BooleanOption value={true} onChange={onChangeFn}/>
        ),
        tree = booleanOption.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle onChange', () => {
        let input = tree.children[0].children[0],
            mockEvent = { target: { checked: true }}
        input.props.onChange(mockEvent)
        expect(onChangeFn).toBeCalledWith(mockEvent.target.checked)
    })
})

describe('StringOption Component', () => {
    let StringOption = Options['str'],
        onChangeFn = jest.fn(),
        stringOption = renderer.create(
            <StringOption value="foo" onChange={onChangeFn}/>
        ),
        tree = stringOption.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle onChange', () => {
        let mockEvent = { target: { value: 'bar' }}
        tree.props.onChange(mockEvent)
        expect(onChangeFn).toBeCalledWith(mockEvent.target.value)
    })

})

describe('NumberOption Component', () => {
    let NumberOption = Options['int'],
        onChangeFn = jest.fn(),
        numberOption = renderer.create(
            <NumberOption value={1} onChange={onChangeFn}/>
        ),
        tree = numberOption.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle onChange', () => {
        let mockEvent = {target: { value: '2'}}
        tree.props.onChange(mockEvent)
        expect(onChangeFn).toBeCalledWith(2)
    })
})

describe('ChoiceOption Component', () => {
    let onChangeFn = jest.fn(),
        choiceOption = renderer.create(
            <ChoicesOption value='a' choices={['a', 'b', 'c']} onChange={onChangeFn}/>
        ),
        tree = choiceOption.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle onChange', () => {
        let mockEvent = { target: {value: 'b'} }
        tree.props.onChange(mockEvent)
        expect(onChangeFn).toBeCalledWith(mockEvent.target.value)
    })
})

describe('StringOption Component', () => {
    let onChangeFn = jest.fn(),
        StringSequenceOption = Options['sequence of str'],
        stringSequenceOption = renderer.create(
            <StringSequenceOption value={['a', 'b']} onChange={onChangeFn}/>
        ),
        tree = stringSequenceOption.toJSON()

    it('should render correctly', () => {
        expect(tree).toMatchSnapshot()
    })

    it('should handle onChange', () => {
        let mockEvent = { target: {value: 'a\nb\nc\n'}}
        tree.props.onChange(mockEvent)
        expect(onChangeFn).toBeCalledWith(['a', 'b', 'c', ''])
    })
})
