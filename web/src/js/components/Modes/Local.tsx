import * as React from 'react';
import Mode, { ModeType } from './Mode';

export default function Local() {
    return (
        <Mode
            title="Local Applications"
            description="Transparently Intercept local application(s)"
            type={ModeType.LOCAL}
        >
            <p>Intercept traffic for</p>
        </Mode>
    );
}