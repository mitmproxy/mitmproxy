#!/usr/bin/env python3
'''
@author: David Shaw, shawd@vmware.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- The MIT License (MIT) ----- 
Filename: ASWBXMLCodePage.py
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
		if tag in self.tagLookup:
			return self.tagLookup[tag]
		return 0xFF
	
	def getTag(self, token):
		if token in self.tokenLookup:
			return self.tokenLookup[token]
		return None
	
	def __repr__(self):
		return str(self.tokenLookup)
