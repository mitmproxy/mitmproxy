import { fetchApi } from "../utils"

export const CMD_RESET = 'reset'

export default class WebsocketBackend {
    constructor(store) {
        this.activeFetches = {}
        this.store = store
        this.connect()
    }

    connect() {
        this.socket = new WebSocket(location.origin.replace('http', 'ws') + '/updates')
        this.socket.addEventListener('open', () => this.onOpen())
        this.socket.addEventListener('close', () => this.onClose())
        this.socket.addEventListener('message', msg => this.onMessage(JSON.parse(msg.data)))
        this.socket.addEventListener('error', error => this.onError(error))
    }

    onOpen() {
        this.fetchData("settings")
        this.fetchData("flows")
        this.fetchData("events")
    }

    fetchData(resource) {
        let queue = []
        this.activeFetches[resource] = queue
        fetchApi(`/${resource}`)
            .then(res => res.json())
            .then(json => {
                // Make sure that we are not superseded yet by the server sending a RESET.
                if (this.activeFetches[resource] === queue)
                    this.receive(resource, json)
            })
    }

    onMessage(msg) {

        if (msg.cmd === CMD_RESET) {
            return this.fetchData(msg.resource)
        }
        if (msg.resource in this.activeFetches) {
            this.activeFetches[msg.resource].push(msg)
        } else {
            let type = `${msg.resource}_${msg.cmd}`.toUpperCase()
            this.store.dispatch({ type, ...msg })
        }
    }

    receive(resource, data) {
        let type = `${resource}_RECEIVE`.toUpperCase()
        this.store.dispatch({ type, cmd: "receive", resource, data })
        let queue = this.activeFetches[resource]
        delete this.activeFetches[resource]
        queue.forEach(msg => this.onMessage(msg))
    }

    onClose() {
        // FIXME
        console.error("onClose", arguments)
    }

    onError() {
        // FIXME
        console.error("onError", arguments)
    }
}
