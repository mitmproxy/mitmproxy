import argparse
import os
import re
from libmproxy import encoding
from urllib2 import unquote 

forbidden_chars = re.compile("[^\\w\\-\\.]")

parser = argparse.ArgumentParser(usage='mitmproxy -s "dirdumper.py [options]"')
parser.add_argument('--dump-dir', type=os.path.abspath, metavar='"./dump"', 
					action="store", default=os.path.abspath("./dump"),
                    help="Directory to dump all objects into.")
parser.add_argument('--dump-request-content', action='store_true',
                    help="Also dump request objects.")

args = None

def start(ctx, argv):
    global args
    args = parser.parse_args(argv[1:])

#We have the problematic situation that a both foo.com/bar
#and foo.com/bar/baz can be both valid files.
#However, we cannot create both a folder and a file both called "baz" in the same directory.
#A possible approach would be using folders for everything and placing __resource__ files in them.
#While this would be a much consistent structure, it doesn't represent the file system very well.
#As this view is for visualization purposes only, we took the approach to append [dir] to conflicting folders.
#to accomplish this, we use a slightly modified version of os.makedirs
def makedirs(directory):
    head,tail = os.path.split(directory)
    if not os.path.isdir(head):
        head = makedirs(head)
        directory = os.path.join(head,tail)
    if(os.path.isfile(directory)): #our special case - rename current dir
        tail += "[dir]"
        directory = os.path.join(head,tail)
        return makedirs(directory)
    if(not os.path.isdir(directory)):
        os.mkdir(directory)  
    return directory

def dump(flow, attr):
	message = getattr(flow, attr)

	#Don't dump empty messages
	if(len(message.content) == 0):
		return
	
	#get host directory name and path directories string
	host = flow.request.host
	if flow.request.port != 80:
		host += "-"+str(flow.request.port)
	pathstr = unquote(
		flow.request.path
			.split("#")[0] #remove hash
			.split("?")[0] #remove queryString
		)
	pathstr = os.path.normpath(pathstr).lstrip("./\\")
	if os.path.basename(pathstr) == "":
		pathstr += "__root__"

	host = host.lstrip("./\\")
	if host == "":
		host = "invalid-host"

	dirty_path = [host] + pathstr.replace("\\","/").split("/")
	path = []
	for pathelem in dirty_path:

		#replace invalid characters with placeholder
		#(don't remove, that could reintroduce relative path changes)
		pathelem = forbidden_chars.sub('_', pathelem)

		#cut off length
		if len(pathelem) >= 35:
			pathelem = pathelem[:15] + "[..]" + pathelem[15:]

		path.append(pathelem)

	#If our path is too long, remove directories in the middle
	dirRemoved = False
	while sum(len(s) for s in path) > 150:
		del path[ len(path) / 2 ]
		dirRemoved = True
	# Add placeholder directory if we removed at least one directory
	if dirRemoved:
		splitpos = (len(path)+1) / 2
		path = path[:splitpos] + ["[...]"] + path[splitpos:]

	filename = os.path.join(args.dump_dir,*path)

	d, filename = os.path.split(filename)
	filename = os.path.join(makedirs(d),filename)

	content = str(message.get_decoded_content())

	#If filename is a directory, rename it.
	if(os.path.isdir(filename)):
		os.rename(filename, filename+"[dir]")

	#Rename if file already exists and content is different
	filename, ext = os.path.splitext(filename)
	appendix = ""
	if attr == "request":
		filename += " (request)"
	while(os.path.isfile(filename+str(appendix)+ext)):
		if os.path.getsize(filename+str(appendix)+ext) == len(content):
			with open(filename+str(appendix)+ext,"rb") as f:
				if(f.read() == content):
					return
		if(appendix == ""):
			appendix = 1
		else:
			appendix += 1
	filename = filename + str(appendix) + ext
				
	with open(filename, 'wb') as f:
		f.write(content)



def request(ctx, flow):
	if args.dump_request_content:
		dump(flow,"request")

def response(ctx, flow):
	dump(flow,"response")

if __name__ == "__main__":
    parser.print_help()
