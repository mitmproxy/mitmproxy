#!/usr/bin/env python3
'''
@author: David Shaw, shawd@vmware.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- The MIT License (MIT) -----
Filename: ASWBXMLByteQueue.py
Copyright (c) 2014, David P. Shaw

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''
from queue import Queue
import logging

class ASWBXMLByteQueue(Queue):

    def __init__(self, wbxmlBytes):

        self.bytesDequeued = 0
        self.bytesEnqueued = 0

        Queue.__init__(self)

        for byte in wbxmlBytes:
            self.put(byte)
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
