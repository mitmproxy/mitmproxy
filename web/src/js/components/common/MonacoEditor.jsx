//not working
import React, { Component, PropTypes } from 'react'

export default class MonacoEditor extends Component {

    constructor(props) {
        super(props)
    }

    onLoad(){
        window.MonacoEnvironment = {
			getWorkerUrl: function(workerId, label) {
				return 'worker-loader-proxy.js';
			}
		};
		require.config({
			paths: {
				vs: '../release/min/vs'
			}
		});

    }


    render() {
        return (
            <div id="container"
                 ref={ref => this.editor = ref}
                 style="width:800px;height:600px;border:1px solid grey"
                 onLoad={this.onLoad()}>
            </div>
        )
    }
}
