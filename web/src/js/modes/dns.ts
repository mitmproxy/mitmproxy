import type { ModeState, RawSpecParts } from ".";
import { includeListenAddress } from ".";

export interface DnsState extends ModeState {}

export const getSpec = (m: DnsState): string => {
    return includeListenAddress("dns", m);
};

export const parseRaw = ({
    listen_host,
    listen_port,
}: RawSpecParts): DnsState => ({
    ui_id: Math.random(),
    active: true,
    listen_host,
    listen_port,
});
