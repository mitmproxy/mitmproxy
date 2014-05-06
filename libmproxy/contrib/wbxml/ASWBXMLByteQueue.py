#!/usr/bin/env python
'''
@author: David Shaw, david.shaw.aw@gmail.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- Apache License, Version 2.0 ----- 
Filename: ASWBXMLByteQueue.py
Copyright 2014, David P. Shaw

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
'''
from Queue import Queue
import logging

class ASWBXMLByteQueue(Queue):

    def __init__(self, wbxmlBytes):
        
        self.bytesDequeued = 0
        self.bytesEnqueued = 0
        
        Queue.__init__(self)

        for byte in wbxmlBytes:
            self.put(ord(byte))
            self.bytesEnqueued += 1
        
        
        logging.debug("Array byte count: %d, enqueued: %d" % (self.qsize(), self.bytesEnqueued))
    
    """
    Created to debug the dequeueing of bytes
    """
    def dequeueAndLog(self):
        singleByte = self.get()
        self.bytesDequeued += 1
        logging.debug("Dequeued byte 0x{0:X} ({1} total)".format(singleByte, self.bytesDequeued))
        return singleByte
    
    """
    Return true if the continuation bit is set in the byte
    """
    def checkContinuationBit(self, byteval):
        continuationBitmask = 0x80
        return (continuationBitmask & byteval) != 0
    
    def dequeueMultibyteInt(self):
        iReturn = 0
        singleByte = 0xFF
         
        while True:
            iReturn <<= 7
            if (self.qsize() == 0):
                break
            else:
                singleByte = self.dequeueAndLog()
            iReturn += int(singleByte & 0x7F)
            if not self.checkContinuationBit(singleByte):
                return iReturn

    def dequeueString(self, length=None):
        if ( length != None):
            currentByte = 0x00
            strReturn = ""
            for i in range(0, length):
                # TODO: Improve this handling. We are technically UTF-8, meaning
                # that characters could be more than one byte long. This will fail if we have
                # characters outside of the US-ASCII range
                if ( self.qsize() == 0 ):
                    break
                currentByte = self.dequeueAndLog()
                strReturn += chr(currentByte)

        else:
            currentByte = 0x00
            strReturn = ""
            while True:
                currentByte = self.dequeueAndLog()
                if (currentByte != 0x00):
                    strReturn += chr(currentByte)
                else:
                    break

        return strReturn

