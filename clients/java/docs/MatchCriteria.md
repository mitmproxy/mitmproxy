

# MatchCriteria

A set of criteria for filtering HTTP Requests and Responses.                          Criteria are AND based, and use python regular expressions for string comparison

## Properties

| Name | Type | Description | Notes |
|------------ | ------------- | ------------- | -------------|
|**url** | **Object** | Request URL regexp to match |  [optional] |
|**page** | **Object** | current|all |  [optional] |
|**status** | **Object** | HTTP Status code to match. |  [optional] |
|**content** | **Object** | Body content regexp content to match |  [optional] |
|**contentType** | **Object** | Content type |  [optional] |
|**websocketMessage** | **Object** | Websocket message text to match |  [optional] |
|**requestHeader** | **Object** |  |  [optional] |
|**requestCookie** | **Object** |  |  [optional] |
|**responseHeader** | **Object** |  |  [optional] |
|**responseCookie** | **Object** |  |  [optional] |
|**jsonValid** | **Object** | Is valid JSON |  [optional] |
|**jsonPath** | **Object** | Has JSON path |  [optional] |
|**jsonSchema** | **Object** | Validates against passed JSON schema |  [optional] |
|**errorIfNoTraffic** | **Object** | If the proxy has NO traffic at all, return error |  [optional] |



