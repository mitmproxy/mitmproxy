import { includeListenAddress, ModeState } from ".";

export interface WireguardState extends ModeState {
    file_path?: string;
}

export const getSpec = (s: WireguardState): string => {
    return includeListenAddress("wireguard", s);
};
