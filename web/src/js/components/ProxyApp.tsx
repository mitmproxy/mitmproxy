import React, { useEffect } from 'react'

import { onKeyDown } from '../ducks/ui/keyboard'
import MainView from './MainView'
import Header from './Header'
import CommandBar from './CommandBar'
import EventLog from './EventLog'
import Footer from './Footer'
import Modal from './Modal/Modal'
import {useAppDispatch, useAppSelector} from "../ducks";

export default function ProxyAppMain() {
    const dispatch = useAppDispatch(),
    showEventLog = useAppSelector(state => state.eventLog.visible)

    useEffect(() => {
        window.addEventListener('keydown', (e) => dispatch(onKeyDown(e)));
        return function cleanup() {
            window.removeEventListener('keydown', (e) => dispatch(onKeyDown(e)));
        }
    })

    return (
        <div id="container" tabIndex={0}>
            <Header/>
            <MainView />
            <CommandBar />
            {showEventLog && (
                <EventLog key="eventlog"/>
            )}
            <Footer />
            <Modal/>
        </div>
    )
}
