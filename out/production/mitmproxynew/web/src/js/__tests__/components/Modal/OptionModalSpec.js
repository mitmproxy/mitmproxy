import React from 'react'
import renderer from 'react-test-renderer'
import { PureOptionDefault } from '../../../components/Modal/OptionModal'

describe('PureOptionDefault Component', () => {

    it('should return null when the value is default', () => {
        let pureOptionDefault = renderer.create(
            <PureOptionDefault value="foo" defaultVal="foo"/>
        ),
            tree = pureOptionDefault.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should handle boolean type', () => {
        let pureOptionDefault = renderer.create(
            <PureOptionDefault value={true} defaultVal={false}/>
        ),
            tree = pureOptionDefault.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should handle array', () => {
        let a = [""], b = [], c = ['c'],
            pureOptionDefault = renderer.create(
                <PureOptionDefault value={a} defaultVal={b}/>
            ),
            tree = pureOptionDefault.toJSON()
        expect(tree).toMatchSnapshot()

        pureOptionDefault = renderer.create(
            <PureOptionDefault value={a} defaultVal={c}/>
        )
        tree = pureOptionDefault.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should handle string', () => {
        let pureOptionDefault = renderer.create(
            <PureOptionDefault value="foo" defaultVal=""/>
        ),
            tree = pureOptionDefault.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should handle null value', () => {
        let pureOptionDefault = renderer.create(
            <PureOptionDefault value="foo" defaultVal={null}/>
        ),
            tree = pureOptionDefault.toJSON()
        expect(tree).toMatchSnapshot()
    })

})
