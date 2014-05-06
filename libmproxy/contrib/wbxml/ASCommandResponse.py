#!/usr/bin/env python
'''
@author: David Shaw, david.shaw.aw@gmail.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- Apache License, Version 2.0 ----- 
Filename: ASCommandResponse.py
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
from ASWBXML import ASWBXML
import logging

class ASCommandResponse:

	def __init__(self, response):
		self.wbxmlBody = response
		try:
			if ( len(response) > 0):
				self.xmlString = self.decodeWBXML(self.wbxmlBody)
			else:
				logging.error("Empty WBXML body passed")
		except Exception as e:
			logging.error("Error: {0}".format(e.message))
			self.xmlString = None

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
		