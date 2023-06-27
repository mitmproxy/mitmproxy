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
from typing import Union, Dict, List, Tuple

logger = logging.getLogger(__name__)
class ReadHar:
    
    def __init__(self):
        self.flows = []
    
    def fix_headers(self, request_headers:Union[List[Dict[str,str]], List[Tuple[str, str]]])->List[Tuple[bytes,bytes]]:
        """Converts provided headers into (b"header-name", b"header-value") tuples"""
        flow_headers = []
        for header in request_headers:

            # Applications that use the {"name":item,"value":item} notation are Brave, Chrome, Edge, Firefox, Charles, Fiddler, Insomnia, Safari
            if isinstance(header,dict):
                try:
                    key=header["name"]
                    value=header["value"]
                except KeyError as e:
                    raise exceptions.OptionsError(str(e)) from e

            # Application that use the [name, value] notation is Slack
            else:
                try:
                    key=header[0]
                    value=header[1]
                except IndexError as e:
                    raise exceptions.OptionsError(str(e)) from e
            flow_headers.append((bytes(key, 'utf-8'),bytes(value, 'utf-8')))

        return flow_headers

    # Don't know how to make a type annotation for the request json
    def request_to_flow(self, request_json:Dict)->http.HTTPFlow:
        """
        Creates a HTTPFlow object from a given entry in HAR file
        """

        request_method = request_json["request"]["method"]
        request_url = request_json["request"].get("url",None)
        if not request_url:
            request_url = request_json["request"].get("host",None)
        
        request_headers = self.fix_headers(request_json["request"].get("headers",[]))

        client_conn = connection.Client(
            peername=(
                "127.0.0.1",
                51513
            ),
            sockname=(
                "127.0.0.1",
                8080
            ),
            #TODO Get time info from HAR File
            timestamp_start=time.time()
        )

        # 375:3 is default mitmproxy server_conn when making a new flow.
        server_conn = connection.Server(address=("375",3))

        newflow = http.HTTPFlow(client_conn,server_conn)
        try:
            newflow.request = http.Request.make(request_method,request_url,"",request_headers)
        except TypeError as e:
            logger.error("Failed to create request")
            raise exceptions.OptionsError(str(e)) from e
            
            
        response_code = request_json["response"].get("status","")
            
        response_content = request_json["response"]["content"].get("text","")
        
        response_headers = self.fix_headers(request_json["response"].get("headers",[]))
        try:
            newflow.response = http.Response.make(response_code,response_content,response_headers)
        except TypeError as e:
            logger.error("Failed to create response")
            raise exceptions.OptionsError(str(e)) from e
        
        return newflow

    async def load_flows(self)->None:
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
                    logger.warning("Flow file corrupted - loaded %i flows." % cnt)
                else:
                    logger.error("Flow file corrupted.")
                raise exceptions.FlowReadException(str(e)) from e
        

       
   
    @command.command("readhar")
    def read_har(self,
        path: types.Path,
        ) -> None:
        """
        Reads a HAR file into mitmproxy. Loads a flow for each entry in given HAR file. 

        Args:
            path (types.Path): Path to HAR file
        """
        with open( path, "r") as fp:
            try:
                harFile = json.load(fp)
            except Exception:
                    logger.error("HAR file was unable to be loaded using json.load()")
                    raise(Exception("Unable to read HAR file. Please provide a valid HAR file"))
        
        for request_json in harFile['log']['entries']:
            flow = self.request_to_flow(request_json)
            if flow: 
                self.flows.append(flow)
        asyncio.create_task(self.load_flows())

addons = [ReadHar()]