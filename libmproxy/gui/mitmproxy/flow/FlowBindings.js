define([
    "dojo/dom-construct",
    "dojo/on", "lodash",
    "highlight",
    "./MessageUtils",
    "./RequestUtils"
], function(domConstruct, on, _, hljs, MessageUtils, RequestUtils) {
  var bindings = {};

  var askPretty = 1024 * 15,
    autoPretty = 1024 * 300;

  bindings.headerTable = function(type, node, message) {

    var html = '<tr><td colspan="2"><h5><i class="icon-' + (message._attr == "request" ? "forward" : "backward") + '"></i> R' + message._attr.substr(1) + ' Headers:</h5></td></tr> ';
    var headers = message.headers;
    for (var i = 0; i < headers.length; i++) {
      html += (
        '<tr>' +
        '<td>' + _.escape(headers[i][0]) + '</td>' +
        '<td>' + _.escape(headers[i][1]) + '</td>' +
        '</tr>');
    }
    node.classList.add("header");
    node.innerHTML = html;
  };

  bindings.checksumTable = function(type, node, message) {

    var html = "";
    for (var item in message.contentChecksums) {
      html += '<tr><td>' + _.escape(item) + '</td><td><ul class="list-unstyled">';

      for (var algo in message.contentChecksums[item]) {
        var checksum = _.escape(message.contentChecksums[item][algo]);
        html += '<li>' + _.escape(algo) +
          ': <span>' + checksum + '</span>';
        //VirusTotal Integration
        if (algo === "sha256") {
          html += ' <a target="_blank" href="https://www.virustotal.com/de/file/' + checksum + '/analysis/">[VT]</a>';
        }
        html += '</li>';
      }

      html += '</ul></td></tr>';
    }
    node.innerHTML = html;
  };

  bindings.formDataTable = function(type, node, request) {
    var self = this;

    if (node._formDataLoading) {
      node._formDataLoading.cancel("outdated");
    }

    if (!RequestUtils.hasFormData(request)) {
      domConstruct.empty(node);
    } else {
        //Add Loading indicator row
        var headerRow = domConstruct.place("<tr><td><h5>Form Data: </h5></td></tr>", node,
          "only");
        var loading = domConstruct.place('<td><i class="icon-refresh"></i> Loading...</td>',headerRow,"last");

        node._formDataLoading = RequestUtils.getFormData(request).then(function(formData) {
          delete node._formDataLoading;

          var fragment = document.createDocumentFragment();
          for (var i = 0; i < formData.length; i++) {
            fragment.appendChild(domConstruct.toDom("<tr><td>" +
              _.escape(decodeURIComponent(formData[i].name)) + "</td><td>" +
              _.escape(decodeURIComponent(formData[i].value)) +
              "</td></tr>"));
          }
          domConstruct.empty(loading);
          domConstruct.place(fragment, node, "last");
        });

        //Destroy request when widget gets destroyed.
        self.own({"remove": node._formDataLoading.cancel.bind(node._contentLoading)});
    }
  };

  // displayContent factory function.
  // This allows us to specify a transform on the content before it gets handled.
  bindings._displayContent = function(contentTransform, nodeTransform) {
    return function(type, node, message) {
      var self = this;

      if (node._contentLoading) {
        node._contentLoading.cancel("outdated");
      }

      node.classList.remove("preview-active");
      node.classList.remove("preview-loading");

      function load() {
        node._contentLoading = MessageUtils.getContent(message, {
          always: true
        }).then(function(content) {
          delete node._contentLoading;
          content = contentTransform ? contentTransform(content) : content;
          node.textContent = content;
          node.classList.remove("preview-loading");
          node.classList.add("preview-active");

          if (nodeTransform) {
            nodeTransform(message, node);
          }

        });

        //Destroy request when widget gets destroyed.
        self.own({"remove": node._contentLoading.cancel.bind(node._contentLoading)});

      }

      if (message && MessageUtils.hasContent(message)) {
        node.classList.add("preview-loading");
        if (MessageUtils.hasLargeContent(message)) {
          var button = domConstruct.place("<button>Load Content (" + MessageUtils.getContentLengthFormatted(message) + ")</button>", node, "only");
          on(button, "click", load);
        } else {
          load();
        }
      }
    };
  };

  bindings._prettifyNodeTransform = function(message, node) {
    function prettify() {
      hljs.highlightBlock(node);
    }

    if (message.contentLength < autoPretty) {
      prettify();
    } else if (message.contentLength < askPretty) {
      //FIXME
    }
  };

  //no transform by default
  bindings.displayContent = bindings._displayContent(undefined, bindings._prettifyNodeTransform);

  return bindings;
});