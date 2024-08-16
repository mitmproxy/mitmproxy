import { includeListenAddress, ModeState, RawSpecParts } from ".";
import { partition } from "../utils";

export enum UpstreamProxyProtocols {
    HTTP = "http",
    HTTPS = "https",
}

export interface UpstreamState extends ModeState {
    protocol: UpstreamProxyProtocols;
    destination: string;
}

export const defaultReverseState = (): UpstreamState => ({
    active: false,
    protocol: UpstreamProxyProtocols.HTTPS,
    destination: "",
    ui_id: Math.random(),
});

export const getSpec = (state: UpstreamState): string => {
    return includeListenAddress(
        `upstream:${state.protocol}://${state.destination}`,
        state,
    );
};

export const parseRaw = ({
    data,
    listen_host,
    listen_port,
}: RawSpecParts): UpstreamState => {
    let [protocol, destination] = partition(data!, "://") as [
        UpstreamProxyProtocols,
        string,
    ];
    if (!destination) {
        destination = protocol;
        protocol = UpstreamProxyProtocols.HTTPS;
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
