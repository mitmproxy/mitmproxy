---
title: "Getting Started"
menu: "overview"
menu:
    overview:
        weight: 3
---

# Getting Started

We assume you have already [installed]({{< relref "overview-installation">}}) mitmproxy on
your machine.

## Launch the tool you need

You can start any of our three tools from the command line / terminal.

* **mitmproxy** gives you an interactive command-line interface
* **mitmweb** gives you a browser-based GUI
* **mitmdump** gives you non-interactive terminal output

If you use the command-line interface, we highly recommend you to take the [tutorial]({{< relref "mitmproxytutorial-userinterface" >}}) to get started.

## Structure of the Proxy usage concept  

Client --------------------> Proxy --------------------> Server  

- Client - is your app. It can be a browser, mobile app or just console util like `curl`  
- Server - is your app that is running on specific host and port.  
- Proxy is just a tool in the middle.  
  It:  
  - catches request from client, makes Client feels like Proxy is an actual server
  - sends it to a Server, makes Server believe that it was an actual Client and sends response all the way back.  

By default **mitmproxy** starts on `http://127.0.0.1:8080/`. If you want to reach your `Proxy` it's a touch point.  

![image](https://user-images.githubusercontent.com/84029657/160138642-b3bccdae-a0e6-4859-ad04-703eb69e8d4c.png)

## Basic usage 

Let's say you have a `Client`(browser) that requests you site on a `localhost:3001`

2 most common [modes](https://docs.mitmproxy.org/stable/concepts-modes/) of work:  
- **regular** mode(default) - you set up your browser to use proxy in a settings. So you request will be `http://localhost:3001` as usual. Browser will send all traffic through a `proxy` implicitly.  
```bash
mitmproxy --mode regular
curl --proxy http://localhost:8080 "http://localhost:3001"
```

- **reverse** mode - you set a mode `option` to reverse traffic for `http://localhost:3001` and use your proxy url directly `http://127.0.0.1:8080/`. Proxy will send's your request to a server(`localhost:3001`).  
```bash
mitmproxy --mode reverse:http://localhost:3001
curl http://localhost:8080
```  

### Options Fully control Proxy  

  All 3 tools are the same Proxy. And you can run them in the same way.  
What you **really** need for controlling behavior, are **options**.  

[all-options](https://docs.mitmproxy.org/stable/concepts-options/)

You can start all 3 tools with a set of options like so.

```bash
mitmproxy --mode reverse:http://localhost:3001
mitmdump --mode reverse:http://localhost:3001
mitmweb --mode reverse:http://localhost:3001
```

For `mitmproxy` and `mitmweb` you can control options from the interface. Start hem without any params, changing needed options later.  

- For `mitmweb` use GUI 
![image](https://user-images.githubusercontent.com/84029657/160147201-bf0b14fb-579d-4cf6-8d76-539550eb84b5.png)

- For `mitmproxy` you need use commands for setting options.  
Let's set mode option.  **set** is a [command](https://docs.mitmproxy.org/stable/addons-commands/).(shift + c list all commands)

  Type `:`  
  -> `set mode reverse:http://localhost:3001`.  
  -> `set intercept '~u /int'`. (intercept all request with url /int).  
  ![image](https://user-images.githubusercontent.com/84029657/160148088-d4cfcf04-d744-46fd-8ed2-0ed3ac489c81.png)

  `~u /int` is a [filter expression](https://docs.mitmproxy.org/stable/concepts-filters/) used for interception.  
  Interception is like a breakPoint. You will need to let intercepted request go by typing `a` for `mitmproxy` or by `Play` button in GUI. One time for request(you will have an option to observe it or even edit), one for response.  
  
  Or by command `flow.resume 1`(2 times for request and response) where 1 is a que number of a waiting requests(in a case you have 2 at the time intercepted requests, second one will be with number 2 waiting for your actions)

  Trigger interception
  ```bash
  curl http://localhost:8080/int
  ```
  ![image](https://user-images.githubusercontent.com/84029657/160148528-92846134-e37b-42ff-b9a6-723cf4d9e640.png)


  Using `set` command is the same as providing such options while starting proxy 
  ```bash
  mitmproxy --mode reverse:http://localhost:3001 --intercept '~u /int'
  ```

  To reset option use command:  
  Type `:`
  -> `options.reset.one mode`.  
  -> `options.reset.one intercept`.  
  Or reset all
  -> `options.reset`

## Configure your browser or device

Mitmproxy starts as a [regular HTTP proxy]({{< relref
"concepts-modes#regular-proxy">}}) by default and listens on `http://localhost:8080`.

You need to configure your browser or device to route all traffic through mitmproxy.
Browser versions and configurations options frequently change, so we recommend to simply search the
web on how to configure an HTTP proxy for your system. Some operating system
have a global settings, some browser have their own, other applications use
environment variables, etc.

You can check that your web traffic is going through mitmproxy by browsing to
http://mitm.it - it should present you with a [simple page]({{< relref
"concepts-certificates#quick-setup">}}) to install the mitmproxy Certificate
Authority - which is also the next step. Follow the instructions for your OS /
system and install the CA.

## Verifying everything works

At this point your running mitmproxy instance should already show the first HTTP
flows from your client. You can test that all TLS-encrypted web traffic is
working as expected by browsing to https://mitmproxy.org - it should show up as
new flow and you can inspect it.

## Resources

* [**GitHub**](https://github.com/mitmproxy/mitmproxy): If you want to ask usage questions, contribute
  to mitmproxy, or submit a bug report, please use GitHub.
* [**Slack**](https://mitmproxy.slack.com): For ephemeral development questions/coordination, please use our Slack channel.
