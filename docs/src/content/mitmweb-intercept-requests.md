---
title: "Intercept Requests"
layout: single
menu:
    mitmweb:
        weight: 2
---

# Intercept Reqeusts

You can intercept HTTP communications using mitmproxy filter expression. The intercepted communications can be modified and resumed.
The intercepted communications is displayed in orange in the flow table like the following.

{{< figure src="/screenshots/intercepted-flow.png" >}}

## how to set a filter in mitmweb

There are 2 ways to set a filter in mitmweb. 

{{< figure src="/screenshots/start-menu2.png" >}}

First, you can specify a filter by entering it in the input field of the start menu.

{{< figure src="/screenshots/quick-actions-menu.png" >}}

Second, you can specify the interception filter from the quick action menu in the flow table.

## how to modify intercepted flows in mitmweb

{{< figure src="/screenshots/pre-edit.png" >}}

When you click a row in the flow table, flow view corresponding to the flow appears. You can edit HTTP headers and content by pressing the pensil button in the upper right of the flow view. 

{{< figure src="/screenshots/post-edit.png" >}}

When you finish modifying the flow, press the check button in the same place as the pensil button was. The change will be applied to the flow.


## how to resume intercepted flows in mitmweb

{{< figure src="/screenshots/resume-flow.png" >}}

There are two ways to resume intercepted flows.

The first one is select the intercepted flow in the flow table and move to the flow section in main menu. Then, press the resume button in the menu.

The other one is press the green arrow button in the right side of the flow row in the flow table. This method is convenient because it allows you to resume the intercepted flow with one click!