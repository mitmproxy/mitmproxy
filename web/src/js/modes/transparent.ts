import { includeListenAddress, ModeState, RawSpecParts } from ".";

export interface TransparentState extends ModeState {}

export const getSpec = (s: TransparentState): string => {
    return includeListenAddress("transparent", s);
};

export const parseRaw = ({
    listen_host,
    listen_port,
}: RawSpecParts): TransparentState => ({
    ui_id: Math.random(),
    active: true,
    listen_host,
    listen_port,
});
