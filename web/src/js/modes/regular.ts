import { includeListenAddress, ModeState } from ".";

export interface RegularState extends ModeState {}

export const getSpec = (m: RegularState): string => {
    return includeListenAddress("regular", m);
};
