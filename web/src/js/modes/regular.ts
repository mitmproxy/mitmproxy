import { includeListenAddress, ModeState, RawSpecParts } from ".";

export interface RegularState extends ModeState {}

export const getSpec = (m: RegularState): string => {
    return includeListenAddress("regular", m);
};

export const parseRaw = ({
    listen_host,
    listen_port,
}: RawSpecParts): RegularState => ({
    ui_id: Math.random(),
    active: true,
    listen_host,
    listen_port,
});
