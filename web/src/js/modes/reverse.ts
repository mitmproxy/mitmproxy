import { includeListenAddress, ModeState, RawSpecParts } from ".";
import { ReverseProxyProtocols } from "../backends/consts";
import { partition } from "../utils";

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

export const parseRaw = ({
    data,
    listen_host,
    listen_port,
}: RawSpecParts): ReverseState => {
    let [protocol, destination] = partition(data!, "://") as [
        ReverseProxyProtocols,
        string,
    ];
    if (!destination) {
        destination = protocol;
        protocol = ReverseProxyProtocols.HTTPS;
    }
    return {
        ui_id: Math.random(),
        active: true,
        protocol,
        destination,
        listen_host,
        listen_port,
    };
};
