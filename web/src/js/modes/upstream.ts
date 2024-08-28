import { includeListenAddress, ModeState, RawSpecParts } from ".";

export interface UpstreamState extends ModeState {
    destination: string;
}

export const defaultReverseState = (): UpstreamState => ({
    active: false,
    destination: "",
    ui_id: Math.random(),
});

export const getSpec = (state: UpstreamState): string => {
    return includeListenAddress(`upstream:${state.destination}`, state);
};

export const parseRaw = ({
    data,
    listen_host,
    listen_port,
}: RawSpecParts): UpstreamState => {
    return {
        ui_id: Math.random(),
        active: true,
        destination: data || "",
        listen_host,
        listen_port,
    };
};
