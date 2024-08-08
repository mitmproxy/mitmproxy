import { includeListenAddress, ModeState, RawSpecParts } from ".";

export interface WireguardState extends ModeState {
    file_path?: string;
}

export const getSpec = (s: WireguardState): string => {
    return includeListenAddress("wireguard", s);
};

export const parseRaw = ({
    data,
    listen_host,
    listen_port,
}: RawSpecParts): WireguardState => ({
    ui_id: Math.random(),
    active: true,
    listen_host,
    listen_port,
    file_path: data,
});
