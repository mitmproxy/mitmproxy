define(["lodash", "dojo/_base/lang", "dojo/Deferred", "../util/formatSize"], function(_, lang, Deferred, formatSize) {
  //Utility functions that are shared by RequestUtils and ResponseUtil

  //TODO: ES6: Implement a caching proxy. Remove custom caching in getHeader

  var contentUrl = function(message, action) {
    return ("/files" +
      "/" + message._flow.id +
      "/" + message._attr +
      "/" + action);
  };


  var MessageUtils = {
    getContentType: function(message) {
      return MessageUtils.getHeader(message, /Content-Type/i);
    },
    hasContent: function(message) {
      return message.contentLength > 0;
    },
    hasLargeContent: function(message) {
      return message.contentLength > 1024 * 1024 * 0.5 /* > 0.5MB */ ;
    },
    getViewUrl: function(message) {
      return contentUrl(message, "inline");
    },
    getDownloadUrl: function(message) {
      return contentUrl(message, "attachment");
    },
    getContent: function(message, options) {
      var def = new Deferred();

      options = lang.mixin({
        responseType: "text",
        range: undefined,
        always: false
      }, options);

      if (!MessageUtils.hasContent(message)) {
        def.resolve("");
        return def;
      }
      if (!options.always && !options.range && message.contentLength > 1024 * 1024 * 1) {
        if (!window.confirm("This request is pretty big and might cause performance issues (" +
          MessageUtils.getContentLengthFormatted(message) +
          ") if we load it. Press OK to continue anyway.")) {

          def.resolve("--- big chunk of data ---");
          return def;
        }
      }
      var xhr = new XMLHttpRequest();
      xhr.open('GET', MessageUtils.getViewUrl(message), true);
      xhr.responseType = options.responseType;

      if (options.range)
        xhr.setRequestHeader("Range", options.range);

      xhr.onload = function() {
        def.resolve(this.response, this);
      };

      xhr.send();

      def.then(undefined, function() {
        xhr.abort();
      });
      return def;
    },
    getContentLengthFormatted: function(message) {
      return formatSize(message.contentLength);
    },
    getHeader: function(message, regex) {
      if (!message._headerLookups)
        Object.defineProperty(message, "_headerLookups", {
          value: {},
          configurable: false,
          enumerable: false,
          writable: false
        });
      if (!(regex in message._headerLookups)) {
        var header;
        for (var i = 0; i < message.headers.length; i++) {
          if ( !! message.headers[i][0].match(regex)) {
            header = message.headers[i];
            break;
          }
        }
        message._headerLookups[regex] = header ? header[1] : undefined;
      }
      return message._headerLookups[regex];
    },
    getRawHeaders: function(message) {
      var rawHeader = "";
      var headers = message.headers;
      for (var i = 0; i < headers.length; i++) {
        rawHeader += headers[i][0] + ": " + headers[i][1] + "\n";
      }
      rawHeader += "\n"; //terminate with \n\n
      return rawHeader;
    },
    getRawFirstLine: function(message) {
      if (message._attr === "request") {
        return [message.method, message.path, "HTTP/" + message.httpversion.join(".")]
          .join(" ") + "\n";
      } else {
        return ["HTTP/" + message.httpversion.join("."), message.code, message.msg]
          .join(" ") + "\n";
      }
    }
  };

  return MessageUtils;
});