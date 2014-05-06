#!/usr/bin/env python
'''
@author: David Shaw, david.shaw.aw@gmail.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- Apache License, Version 2.0 ----- 
Filename: ASWBXMLCodePage.py
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
class ASWBXMLCodePage:
	def __init__(self):
		self.namespace = ""
		self.xmlns = ""
		self.tokenLookup = {}
		self.tagLookup = {}
	
	def addToken(self, token, tag):
		self.tokenLookup[token] = tag
		self.tagLookup[tag] = token
	
	def getToken(self, tag):
		if self.tagLookup.has_key(tag):
			return self.tagLookup[tag]
		return 0xFF
	
	def getTag(self, token):
		if self.tokenLookup.has_key(token):
			return self.tokenLookup[token]
		return None
	
	def __repr__(self):
		return str(self.tokenLookup)