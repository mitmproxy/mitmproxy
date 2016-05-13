#!/usr/bin/env python
'''
@author: David Shaw, david.shaw.aw@gmail.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- The MIT License (MIT) ----- 
Filename: ASCommandResponse.py
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
from .ASWBXML import ASWBXML
import logging

class ASCommandResponse:

	def __init__(self, response):
		self.wbxmlBody = response
		try:
			if ( len(response) > 0):
				self.xmlString = self.decodeWBXML(self.wbxmlBody)
			else:
				raise ValueError("Empty WBXML body passed")
		except Exception as e:
			self.xmlString = None
			raise ValueError("Error: {0}".format(e.message))

	def getWBXMLBytes(self):
		return self.wbxmlBytes
	
	def getXMLString(self):
		return self.xmlString
	
	def decodeWBXML(self, body):
		self.instance = ASWBXML()
		self.instance.loadBytes(body)
		return self.instance.getXml()

if __name__ == "__main__":
	import os	
	logging.basicConfig(level=logging.INFO)

	projectDir = os.path.dirname(os.path.realpath("."))
	samplesDir = os.path.join(projectDir, "Samples/")
	listOfSamples = os.listdir(samplesDir)

	for filename in listOfSamples:
		byteWBXML = open(samplesDir + os.sep + filename, "rb").read()
		
		logging.info("-"*100)
		logging.info(filename)
		logging.info("-"*100)
		instance = ASCommandResponse(byteWBXML)
		logging.info(instance.xmlString)
