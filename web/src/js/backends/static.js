/*
 * This backend uses the REST API only to host static instances,
 * without any Websocket connection.
 */
import { fetchApi } from "../utils"

const CMD_RESET = 'reset'

export default class StaticBackend {
   constructor(store) {
       this.activeFetches = {}
       this.store = store
       this.onOpen()
   }

   onOpen() {
        this.fetchData("settings")
        this.fetchData("flows")
        this.fetchData("events")
        this.fetchData("options")
   }

   fetchData(resource) {
       let queue = []
       this.activeFetches[resource] = queue
       fetchApi(`/${resource}`)
           .then(res => res.json())
           .then(json => {
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
           this.store.dispatch({ type, ...msg})
       }
   }

   receive(resource, data) {
       let type = `${resource}_RECEIVE`.toUpperCase()
       this.store.dispatch({ type, cmd: "receive", resource, data })
       let queue = this.activeFetches[resource]
       delete this.activeFetches[resource]
       queue.forEach(msg => this.onMessage(msg))
   }

}
