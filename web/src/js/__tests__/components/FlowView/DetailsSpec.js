import React from 'react'
import renderer from 'react-test-renderer'
import Details, { TimeStamp, ConnectionInfo, CertificateInfo, Timing } from '../../../components/FlowView/Details'
import { TFlow } from '../../ducks/tutils'

let tflow = TFlow()

describe('TimeStamp Component', () => {
    it('should render correctly', () => {
        let timestamp = renderer.create(<TimeStamp t={1483228800} deltaTo={1483228700} title="foo"/>),
            tree = timestamp.toJSON()
        expect(tree).toMatchSnapshot()
        // without timestamp
        timestamp = renderer.create(<TimeStamp/>)
        tree = timestamp.toJSON()
        expect(tree).toMatchSnapshot()
    })
})

describe('ConnectionInfo Component', () => {
    it('should render correctly', () => {
        let connectionInfo = renderer.create(<ConnectionInfo conn={tflow.client_conn}/>),
            tree = connectionInfo.toJSON()
        expect(tree).toMatchSnapshot()
    })
})

describe('CertificateInfo Component', () => {
    it('should render correctly', () => {
        let certificateInfo = renderer.create(<CertificateInfo flow={tflow}/>),
            tree = certificateInfo.toJSON()
        expect(tree).toMatchSnapshot()
    })
})

describe('Timing Component', () => {
    it('should render correctly', () => {
        let timing = renderer.create(<Timing flow={tflow}/>),
            tree = timing.toJSON()
        expect(tree).toMatchSnapshot()
    })
})

describe('Details Component', () => {
    it('should render correctly', () => {
        let details = renderer.create(<Details flow={tflow}/>),
            tree = details.toJSON()
        expect(tree).toMatchSnapshot()
    })
})
