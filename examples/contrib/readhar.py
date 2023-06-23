"""Reads HAR files into flow objects"""

import logging
import json
import time
from mitmproxy import command
from mitmproxy import connection
from mitmproxy import http
from mitmproxy import types
from mitmproxy.log import ALERT
from mitmproxy import ctx
from mitmproxy import exceptions
import asyncio
import codecs

class ReadHar:
    def __init__(self):
        self.harFile = {}
        self.flows = []
    
    def fix_headers(self, request_headers):
        """Changes provided headers into flow-friendly format"""
        flow_headers = []
        for header in request_headers:
            if type(header) == dict and header.get("name",None):
                key=header["name"]
                value=header["value"]
            else:
                key=header[0]
                value=header[1]
            flow_headers.append((bytes(key, 'utf-8'),bytes(value, 'utf-8')))

        return flow_headers

    
    def request_to_flow(self, request_json):
        """
        Creates a HTTPFlow object from a given entry in HAR file
        """

        requestMethod = request_json["request"].get("method","")
        requestUrl = request_json["request"].get("url",None)
        if not requestUrl:
            requestUrl = request_json["request"].get("host",None)
        
        requestHeaders = self.fix_headers(request_json["request"].get("headers",[]))

        client_conn = connection.Client(
            peername=(
                "127.0.0.1",
                51513
            ),
            sockname=(
                "127.0.0.1",
                8080
            ),
            timestamp_start=time.time()
        )
        server_conn = connection.Server(address=None)

        newflow = http.HTTPFlow(client_conn,server_conn)
        try:
            newflow.request = http.Request.make(requestMethod,requestUrl,"",requestHeaders)
        except:
            logging.error("Unable to create flow, please change to a valid HAR format")
            return
            
        responseCode = request_json["response"].get("status","")
            
        responseContent = request_json["response"]["content"].get("text","")
        
        responseHeaders = self.fix_headers(request_json["response"].get("headers",[]))
        try:
            newflow.response = http.Response.make(responseCode,responseContent,responseHeaders)
        except:
            logging.error("Unable to create flow, please change to a valid HAR format")
            return
        
        return newflow

    async def loadFlows(self)->None:
        """
        Loads flows into mitmproxy

        Raises:
            exceptions.FlowReadException: If unable to load flow the FlowReadException is raised
        """
        cnt = 0
        for flow in self.flows:
            try:
                await ctx.master.load_flow(flow)
                cnt+=1
            except (OSError, exceptions.FlowReadException) as e:
                if cnt:
                    logging.warning("Flow file corrupted - loaded %i flows." % cnt)
                else:
                    logging.error("Flow file corrupted.")
                raise exceptions.FlowReadException(str(e)) from e
       
    def running(self):
            """
            Runs the loadFlows function
            """
            self._read_har_task = asyncio.create_task(self.loadFlows())
    @command.command("readhar")
    def readhar(self,
        path: types.Path,
        ) -> None:
        """
        Reads a HAR file into mitmproxy. Loads a flow for each entry in given HAR file. 

        Args:
            path (types.Path): Path to HAR file
        """
        with open( path, "r") as fp:
            try:
                self.harFile = json.load(fp)
            except:
                try:
                    json.load(codecs.open(path, 'r', 'utf-8-sig'))
                except:
                    logging.error("Unable to read HAR file. Please provide a valid HAR file")
                    return
        
        for request_json in self.harFile['log']['entries']:
            flow = self.request_to_flow(request_json)
            if flow: 
                self.flows.append(flow)
        self.running()
        self._read_har_task
        
        
    

addons = [ReadHar()]