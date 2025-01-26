import { includeListenAddress, ModeState, RawSpecParts } from ".";

export interface SocksState extends ModeState {}

export const getSpec = (s: SocksState): string => {
    return includeListenAddress("socks5", s);
};

export const parseRaw = ({
    listen_host,
    listen_port,
}: RawSpecParts): SocksState => ({
    ui_id: Math.random(),
    active: true,
    listen_host,
    listen_port,
});
