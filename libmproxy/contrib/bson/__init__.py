#!/usr/bin/python -OOOO
# vim: set fileencoding=utf8 shiftwidth=4 tabstop=4 textwidth=80 foldmethod=marker :
# Copyright (c) 2010, Kou Man Tong. All rights reserved.
# For licensing, see LICENSE file included in the package.
"""
BSON serialization and deserialization logic.
Specifications taken from: http://bsonspec.org/#/specification
The following types are unsupported, because for data exchange purposes, they're
over-engineered:
	0x06 (Undefined)
	0x07 (ObjectId)
	0x0b (Regex - Exactly which flavor do you want? Better let higher level
		programmers make that decision.)
	0x0c (DBPointer)
	0x0d (JavaScript code)
	0x0e (Symbol)
	0x0f (JS w/ scope)
	0x11 (MongoDB-specific timestamp)

For binaries, only the default 0x0 type is supported.


>>> a = {
...   u"Item A" : u"String item A",
...   u"Item D" : {u"ROFLOL" : u"Blah blah blah"},
...   u"Item C" : [1, 123456789012345, None, "Party and Bad Romance"],
...   u"Item B" : u"\u4e00\u9580\u4e94\u5091"
... }
>>> def sorted(obj, dfs_stack):
...   keys = obj.keys()
...   keys.sort()
...   for i in keys: yield i
... 
>>> def reverse(obj, dfs_stack):
...   keys = obj.keys()
...   keys.sort(reverse = True)
...   for i in keys: yield i
... 
>>> serialized = dumps(a, sorted)
>>> serialized
'\\x9f\\x00\\x00\\x00\\x02Item A\\x00\\x0e\\x00\\x00\\x00String item A\\x00\\x02Item B\\x00\\r\\x00\\x00\\x00\\xe4\\xb8\\x80\\xe9\\x96\\x80\\xe4\\xba\\x94\\xe5\\x82\\x91\\x00\\x04Item C\\x007\\x00\\x00\\x00\\x100\\x00\\x01\\x00\\x00\\x00\\x121\\x00y\\xdf\\r\\x86Hp\\x00\\x00\\n2\\x00\\x053\\x00\\x15\\x00\\x00\\x00\\x00Party and Bad Romance\\x00\\x03Item D\\x00 \\x00\\x00\\x00\\x02ROFLOL\\x00\\x0f\\x00\\x00\\x00Blah blah blah\\x00\\x00\\x00'
>>> 
>>> b = loads(serialized)
>>> b
{u'Item C': [1, 123456789012345, None, 'Party and Bad Romance'], u'Item B': u'\\u4e00\\u9580\\u4e94\\u5091', u'Item A': u'String item A', u'Item D': {u'ROFLOL': u'Blah blah blah'}}
>>> reverse_serialized = dumps(a, reverse)
>>> reverse_serialized
'\\x9f\\x00\\x00\\x00\\x03Item D\\x00 \\x00\\x00\\x00\\x02ROFLOL\\x00\\x0f\\x00\\x00\\x00Blah blah blah\\x00\\x00\\x04Item C\\x007\\x00\\x00\\x00\\x100\\x00\\x01\\x00\\x00\\x00\\x121\\x00y\\xdf\\r\\x86Hp\\x00\\x00\\n2\\x00\\x053\\x00\\x15\\x00\\x00\\x00\\x00Party and Bad Romance\\x00\\x02Item B\\x00\\r\\x00\\x00\\x00\\xe4\\xb8\\x80\\xe9\\x96\\x80\\xe4\\xba\\x94\\xe5\\x82\\x91\\x00\\x02Item A\\x00\\x0e\\x00\\x00\\x00String item A\\x00\\x00'
>>> c = loads(reverse_serialized)
>>> c
{u'Item C': [1, 123456789012345, None, 'Party and Bad Romance'], u'Item B': u'\\u4e00\\u9580\\u4e94\\u5091', u'Item A': u'String item A', u'Item D': {u'ROFLOL': u'Blah blah blah'}}
"""

from codec import *
import network
__all__ = ["loads", "dumps"]

# {{{ Serialization and Deserialization
def dumps(obj, generator = None):
	"""
	Given a dict, outputs a BSON string.

	generator is an optional function which accepts the dictionary/array being
	encoded, the current DFS traversal stack, and outputs an iterator indicating
	the correct encoding order for keys.
	"""
	if isinstance(obj, BSONCoding):
		return encode_object(obj, [], generator_func = generator)
	return encode_document(obj, [], generator_func = generator)

def loads(data):
	"""
	Given a BSON string, outputs a dict.
	"""
	return decode_document(data, 0)[1]
# }}}
# {{{ Socket Patchers
def patch_socket():
	"""
	Patches the Python socket class such that sockets can send and receive BSON
	objects atomically.

	This adds the following functions to socket:

	recvbytes(bytes_needed, sock_buf = None) - reads bytes_needed bytes
	atomically. Returns None if socket closed.

	recvobj() - reads a BSON document from the socket atomically and returns
	the deserialized dictionary. Returns None if socket closed.

	sendobj(obj) - sends a BSON document to the socket atomically. 
	"""
	from socket import socket
	socket.recvbytes = network._recvbytes
	socket.recvobj = network._recvobj
	socket.sendobj = network._sendobj
# }}}
