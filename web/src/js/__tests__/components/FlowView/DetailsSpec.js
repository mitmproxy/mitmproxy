import * as React from "react"
import renderer from 'react-test-renderer'
import Connection, { TimeStamp, ConnectionInfo, CertificateInfo, Timing } from '../../../components/FlowView/Connection'
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
        let details = renderer.create(<Connection flow={tflow}/>),
            tree = details.toJSON()
        expect(tree).toMatchSnapshot()
    })

    it('should render correctly when server address is missing', () => {
        let tflowServerAddressNull = tflow

        tflowServerAddressNull.server_conn.address = null
        tflowServerAddressNull.server_conn.ip_address = null
        tflowServerAddressNull.server_conn.sni = null
        tflowServerAddressNull.server_conn.ssl_established = false
        tflowServerAddressNull.server_conn.tls_version = null
        tflowServerAddressNull.server_conn.timestamp_tcp_setup = null
        tflowServerAddressNull.server_conn.timestamp_ssl_setup = null
        tflowServerAddressNull.server_conn.timestamp_start = null
        tflowServerAddressNull.server_conn.timestamp_end = null

        let details = renderer.create(<Connection flow={tflowServerAddressNull}/>),
            tree = details.toJSON()
        expect(tree).toMatchSnapshot()
    })

})
