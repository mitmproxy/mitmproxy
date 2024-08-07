import { includeListenAddress, ModeState } from ".";
import { ReverseProxyProtocols } from "../backends/consts";

export interface ReverseState extends ModeState {
    protocol: ReverseProxyProtocols;
    destination: string;
}

export const getSpec = (state: ReverseState): string => {
    return includeListenAddress(
        `reverse:${state.protocol}://${state.destination}`,
        state,
    );
};
