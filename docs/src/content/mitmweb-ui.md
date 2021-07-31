---
title: "User Interface"
layout: single
menu:
    mitmweb:
        weight: 1
---

# Overview
The following image shows the overall picture of mitmweb. Each component is described below.

{{< figure src="/screenshots/mitmweb-overview.png" >}}

## main menu
The main menu is the area at the top of the screen, and has four sections (mitmproxy, Start, Options, Flow).

### mitmproxy menu
{{< figure src="/screenshots/mitmweb-dropdown.png" >}}

You can save the flows and open the saved flows. You can also clear all the flows in the flow table.

### start menu
{{< figure src="/screenshots/start-menu1.png" >}}
{{< figure src="/screenshots/start-menu2.png" >}}

You can search, highlight and filter flows using filter expressions in mitmproxy. All intercepted flows are resumed by pressing "Resume All" button.

### options menu
{{< figure src="/screenshots/options-menu.png" >}}

You can edit all available options in mitmweb by pressing the "Edit Options" button.

### flow menu
{{< figure src="/screenshots/main-menu.png" >}}

You can replay, duplicate, revert and delete the selected flow using the buttons. If the selected flow is intercepted, you can also resume or abort it.

## flow table
{{< figure src="/screenshots/flow-table.png" >}}

You can view all HTTP traffic going through mitmweb here. When you hover your mouse over each line, a quick-actions menu appears in the right side. The quick-actions menu have some useful functionalities, where you can copy the flow as various formats and make an interception rule related to the flow. 

## flow view
{{< figure src="/screenshots/flow-view.png" >}}

When you click a row of the flow table, the flow view for the selected flow appears. The flow view has three sections (Request, Response, Details). 

### Request section
This section shows you HTTP request headers and content. You can edit HTTP headers and content by clicking the pencil button in the upper right of the image.

### Response section
This section shows you HTTP response headers and content. You can edit HTTP headers and content by clicking the pencil button in the upper right of the image.

### Details section
This section shows you TLS connection info and timestamps.

## command bar
{{< figure src="/screenshots/command-bar.png" >}}

You can use powerful mitmproxy commands here. The input field has autocompletion functionality. If you press Tab, the input field is autocompleted from the available commands. The popup shows you the command description, arguments, and its return value.