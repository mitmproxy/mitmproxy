import reduceConnection from "../../ducks/connection"
import * as ConnectionActions from "../../ducks/connection"
import { ConnectionState } from "../../ducks/connection"

describe('connection reducer', () => {
    it('should return initial state', () => {
        expect(reduceConnection(undefined, {})).toEqual({
            state: ConnectionState.INIT,
            message: null,
        })
    })

    it('should handle start fetch', () => {
        expect(reduceConnection(undefined, ConnectionActions.startFetching())).toEqual({
            state: ConnectionState.FETCHING,
            message: undefined,
        })
    })

    it('should handle connection established', () => {
        expect(reduceConnection(undefined, ConnectionActions.connectionEstablished())).toEqual({
            state: ConnectionState.ESTABLISHED,
            message: undefined,
        })
    })

    it('should handle connection error', () => {
        expect(reduceConnection(undefined, ConnectionActions.connectionError("no internet"))).toEqual({
            state: ConnectionState.ERROR,
            message: "no internet",
        })
    })

    it('should handle offline mode', () => {
        expect(reduceConnection(undefined, ConnectionActions.setOffline())).toEqual({
            state: ConnectionState.OFFLINE,
            message: undefined,
        })
    })

})
