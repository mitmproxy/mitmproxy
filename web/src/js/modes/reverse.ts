import { includeListenAddress, ModeState } from ".";
import { ReverseProxyProtocols } from "../backends/consts";

export interface ReverseState extends ModeState {
    protocol: ReverseProxyProtocols;
    destination: string;
}

export const defaultReverseState = (): ReverseState => ({
    active: false,
    protocol: ReverseProxyProtocols.HTTPS,
    destination: "",
    ui_id: Math.random(),
});

export const getSpec = (state: ReverseState): string => {
    return includeListenAddress(
        `reverse:${state.protocol}://${state.destination}`,
        state,
    );
};
