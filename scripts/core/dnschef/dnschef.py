#!/usr/bin/env python
#
# DNSChef is a highly configurable DNS Proxy for Penetration Testers 
# and Malware Analysts. Please visit http://thesprawl.org/projects/dnschef/
# for the latest version and documentation. Please forward all issues and
# concerns to iphelix [at] thesprawl.org.
#
# VERSION 0.2.1
#
# Copyright (C) 2013 Peter Kacherginsky
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met: 
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer. 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution. 
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from optparse import OptionParser,OptionGroup
from ConfigParser import ConfigParser
from dnslib import *
from IPy import IP

import threading, random, operator, time
import SocketServer, socket, sys, os
import binascii

from libmproxy.flow import Flow, Request, Response, ClientConnect
from netlib.odict import ODictCaseless
ctx = None
server = None
def add_flow(address,request,response):
    flow = Flow(
            Request(
                client_conn=ClientConnect(address), 
                httpversion=[1,1], 
                host="dnschef",
                port=53, 
                scheme="dns", 
                method="DNS", 
                path="/%s/%s-record" % (str(request.q.qname),str(QTYPE[request.q.qtype]).lower()), 
                headers=ODictCaseless([["Content-Type","dnschef/%srecord" % str(QTYPE[request.q.qtype]).lower()]]),
                content=str(request)))
    flow.response = Response(flow.request,
                        [1,1],
                        200, "FAKE-HTTP",
                        ODictCaseless([["Content-Type","dnschef/%s-record" % str(QTYPE[request.q.qtype]).lower()]]),
                        str(response), 
                        None)
    ctx._master.load_flow(flow)


# DNSHandler Mixin. The class contains generic functions to parse DNS requests and
# calculate an appropriate response based on user parameters.
class DNSHandler():
           
    def parse(self,data):
        response = ""
    
        try:
            # Parse data as DNS        
            d = DNSRecord.parse(data)

        except Exception, e:
            print "[%s] %s: ERROR: %s" % (time.strftime("%H:%M:%S"), self.client_address[0], "invalid DNS request")

        else:        
            # Only Process DNS Queries
            if QR[d.header.qr] == "QUERY":  
                     
                # Gather query parameters
                qname = str(d.q.qname)
                qtype = QTYPE[d.q.qtype]
                
                # Find all matching fake DNS records for the query name or get False
                fake_records = dict()
                for record in self.server.nametodns:
                    fake_records[record] = self.findnametodns(qname,self.server.nametodns[record])
                
                # Check if there is a fake record for the current request qtype
                if qtype in fake_records and fake_records[qtype]:

                    fake_record = fake_records[qtype]

                    response = DNSRecord(DNSHeader(id=d.header.id, bitmap=d.header.bitmap,qr=1, aa=1, ra=1), q=d.q)

                    print "[%s] %s: cooking the response of type '%s' for %s to %s" % (time.strftime("%H:%M:%S"), self.client_address[0], qtype, qname, fake_record)

                    # IPv6 needs additional work before inclusion:
                    if qtype == "AAAA":
                        ipv6 = IP(fake_record)
                        ipv6_bin = ipv6.strBin()
                        ipv6_hex_tuple = [int(ipv6_bin[i:i+8],2) for i in xrange(0,len(ipv6_bin),8)]
                        response.add_answer(RR(qname, QTYPE[qtype], rdata=RDMAP[qtype](ipv6_hex_tuple)))

                    elif qtype == "SOA":
                        mname,rname,t1,t2,t3,t4,t5 = fake_record.split(" ")
                        times = tuple([int(t) for t in [t1,t2,t3,t4,t5]])

                        # dnslib doesn't like trailing dots
                        if mname[-1] == ".": mname = mname[:-1]
                        if rname[-1] == ".": rname = rname[:-1]

                        response.add_answer(RR(qname, QTYPE[qtype], rdata=RDMAP[qtype](mname,rname,times)))

                    elif qtype == "NAPTR":
                        order,preference,flags,service,regexp,replacement = fake_record.split(" ")
                        order = int(order)
                        preference = int(preference)

                        # dnslib doesn't like trailing dots
                        if replacement[-1] == ".": replacement = replacement[:-1]

                        response.add_answer(RR(qname, QTYPE[qtype], rdata=RDMAP[qtype](order,preference,flags,service,regexp,DNSLabel(replacement))))

                    else:
                        # dnslib doesn't like trailing dots
                        if fake_record[-1] == ".": fake_record = fake_record[:-1]
                        response.add_answer(RR(qname, QTYPE[qtype], rdata=RDMAP[qtype](fake_record)))

                    response = response.pack()                   

                elif qtype == "*" and not None in fake_records.values():
                    print "[%s] %s: cooking the response of type '%s' for %s with %s" % (time.strftime("%H:%M:%S"), self.client_address[0], "ANY", qname, "all known fake records.")

                    response = DNSRecord(DNSHeader(id=d.header.id, bitmap=d.header.bitmap,qr=1, aa=1, ra=1), q=d.q)

                    for qtype,fake_record in fake_records.items():
                        if fake_record:

                            # NOTE: RDMAP is a dictionary map of qtype strings to handling classses
                            # IPv6 needs additional work before inclusion:
                            if qtype == "AAAA":
                                ipv6 = IP(fake_record)
                                ipv6_bin = ipv6.strBin()
                                fake_record = [int(ipv6_bin[i:i+8],2) for i in xrange(0,len(ipv6_bin),8)]

                            elif qtype == "SOA":
                                mname,rname,t1,t2,t3,t4,t5 = fake_record.split(" ")
                                times = tuple([int(t) for t in [t1,t2,t3,t4,t5]])

                                # dnslib doesn't like trailing dots
                                if mname[-1] == ".": mname = mname[:-1]
                                if rname[-1] == ".": rname = rname[:-1]

                                response.add_answer(RR(qname, QTYPE[qtype], rdata=RDMAP[qtype](mname,rname,times)))

                            elif qtype == "NAPTR":
                                order,preference,flags,service,regexp,replacement = fake_record.split(" ")
                                order = int(order)
                                preference = int(preference)

                                # dnslib doesn't like trailing dots
                                if replacement and replacement[-1] == ".": replacement = replacement[:-1]

                                response.add_answer(RR(qname, QTYPE[qtype], rdata=RDMAP[qtype](order,preference,flags,service,regexp,replacement)))
                            else:
                                # dnslib doesn't like trailing dots
                                if fake_record[-1] == ".": fake_record = fake_record[:-1]
                                response.add_answer(RR(qname, QTYPE[qtype], rdata=RDMAP[qtype](fake_record)))

                    response = response.pack()

                # Proxy the request
                else:
                    print "[%s] %s: proxying the response of type '%s' for %s" % (time.strftime("%H:%M:%S"), self.client_address[0], qtype, qname)

                    nameserver_tuple = random.choice(self.server.nameservers).split('#')               
                    response = self.proxyrequest(data,*nameserver_tuple)
                
        return response         
    

    # Find appropriate ip address to use for a queried name. The function can 
    def findnametodns(self,qname,nametodns):
    
        # Split and reverse qname into components for matching.
        qnamelist = qname.split('.')
        qnamelist.reverse()
    
        # HACK: It is important to search the nametodns dictionary before iterating it so that
        # global matching ['*.*.*.*.*.*.*.*.*.*'] will match last. Use sorting for that.
        for domain,host in sorted(nametodns.iteritems(), key=operator.itemgetter(1)):
            domain = domain.split('.')
            domain.reverse()
            
            # Compare domains in reverse.
            for a,b in map(None,qnamelist,domain):
                if a != b and b != "*":
                    break
            else:
                # Could be a real IP or False if we are doing reverse matching with 'truedomains'
                return host
        else:
            return False
    
    # Obtain a response from a real DNS server.
    def proxyrequest(self, request, host, port="53"):
        reply = None
        try:
            if self.server.ipv6:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            sock.settimeout(3.0)

            # Send the proxy request to a randomly chosen DNS server
            sock.sendto(request, (host, int(port)))
            reply = sock.recv(1024)
            sock.close()

        except Exception, e:
            print "[!] Could not proxy request: %s" % e
        else:
            return reply 

# UDP DNS Handler for incoming requests
class UDPHandler(DNSHandler, SocketServer.BaseRequestHandler):

    def handle(self):
        (data,socket) = self.request
        response = self.parse(data)

        add_flow(self.client_address,DNSRecord.parse(data),DNSRecord.parse(response))
        
        if response:
            socket.sendto(response, self.client_address)

# TCP DNS Handler for incoming requests            
class TCPHandler(DNSHandler, SocketServer.BaseRequestHandler):

    def handle(self):
        data = self.request.recv(1024)
        
        # Remove the addition "length" parameter used in
        # TCP DNS protocol
        data = data[2:]
        response = self.parse(data)

        add_flow(self.client_address,DNSRecord.parse(data),DNSRecord.parse(response))
        
        if response:
            # Calculate and add the additional "length" parameter
            # used in TCP DNS protocol 
            length = binascii.unhexlify("%04x" % len(response))            
            self.request.sendall(length+response)            

class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):

    # Override SocketServer.UDPServer to add extra parameters
    def __init__(self, server_address, RequestHandlerClass, nametodns, nameservers, ipv6):
        self.nametodns  = nametodns
        self.nameservers = nameservers
        self.ipv6        = ipv6
        self.address_family = socket.AF_INET6 if self.ipv6 else socket.AF_INET

        SocketServer.UDPServer.__init__(self,server_address,RequestHandlerClass) 

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    
    # Override default value
    allow_reuse_address = True

    # Override SocketServer.TCPServer to add extra parameters
    def __init__(self, server_address, RequestHandlerClass, nametodns, nameservers, ipv6):
        self.nametodns  = nametodns
        self.nameservers = nameservers
        self.ipv6        = ipv6
        self.address_family = socket.AF_INET6 if self.ipv6 else socket.AF_INET

        SocketServer.TCPServer.__init__(self,server_address,RequestHandlerClass) 
        
# Initialize and start the DNS Server        
def start_cooking(interface, nametodns, nameservers, tcp=False, ipv6=False, port="53"):
    try:
        global server
        if tcp:
            print "[*] DNSChef is running in TCP mode"
            server = ThreadedTCPServer((interface, int(port)), TCPHandler, nametodns, nameservers, ipv6)
        else:
            server = ThreadedUDPServer((interface, int(port)), UDPHandler, nametodns, nameservers, ipv6)

        # Start a thread with the server -- that thread will then start one
        # more threads for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        
        # Loop in the main thread
        #while True: time.sleep(100)

    except (KeyboardInterrupt, SystemExit):
        server.shutdown()
        print "[*] DNSChef is shutting down."
        sys.exit()

def done(ctx):
    if server:
        print "[*] DNSChef is shutting down."
        server.shutdown()

def start(_ctx, argv=[]): #FIXME remove mitmproxy 0.9 compatibility
    global ctx
    ctx = _ctx

    header  = "          _                _          __  \n"
    header += "         | | version 0.2  | |        / _| \n"
    header += "       __| |_ __  ___  ___| |__   ___| |_ \n"
    header += "      / _` | '_ \/ __|/ __| '_ \ / _ \  _|\n"
    header += "     | (_| | | | \__ \ (__| | | |  __/ |  \n"
    header += "      \__,_|_| |_|___/\___|_| |_|\___|_|  \n"
    header += "                   iphelix@thesprawl.org  \n"

    # Parse command line arguments
    parser = OptionParser(usage = "dnschef.py [options]:\n" + header, description="DNSChef is a highly configurable DNS Proxy for Penetration Testers and Malware Analysts. It is capable of fine configuration of which DNS replies to modify or to simply proxy with real responses. In order to take advantage of the tool you must either manually configure or poison DNS server entry to point to DNSChef. The tool requires root privileges to run on privileged ports." )
    
    fakegroup = OptionGroup(parser, "Fake DNS records:")
    fakegroup.add_option('--fakeip', metavar="192.0.2.1", action="store", help='IP address to use for matching DNS queries. If you use this parameter without specifying domain names, then all \'A\' queries will be spoofed. Consider using --file argument if you need to define more than one IP address.')
    fakegroup.add_option('--fakeipv6', metavar="2001:db8::1", action="store", help='IPv6 address to use for matching DNS queries. If you use this parameter without specifying domain names, then all \'AAAA\' queries will be spoofed. Consider using --file argument if you need to define more than one IPv6 address.')
    fakegroup.add_option('--fakemail', metavar="mail.fake.com", action="store", help='MX name to use for matching DNS queries. If you use this parameter without specifying domain names, then all \'MX\' queries will be spoofed. Consider using --file argument if you need to define more than one MX record.')
    fakegroup.add_option('--fakealias', metavar="www.fake.com", action="store", help='CNAME name to use for matching DNS queries. If you use this parameter without specifying domain names, then all \'CNAME\' queries will be spoofed. Consider using --file argument if you need to define more than one CNAME record.')
    fakegroup.add_option('--fakens', metavar="ns.fake.com", action="store", help='NS name to use for matching DNS queries. If you use this parameter without specifying domain names, then all \'NS\' queries will be spoofed. Consider using --file argument if you need to define more than one NS record.')
    fakegroup.add_option('--file', action="store", help="Specify a file containing a list of DOMAIN=IP pairs (one pair per line) used for DNS responses. For example: google.com=1.1.1.1 will force all queries to 'google.com' to be resolved to '1.1.1.1'. IPv6 addresses will be automatically detected. You can be even more specific by combining --file with other arguments. However, data obtained from the file will take precedence over others.")
    parser.add_option_group(fakegroup)

    parser.add_option('--fakedomains', metavar="thesprawl.org,google.com", action="store", help='A comma separated list of domain names which will be resolved to FAKE values specified in the the above parameters. All other domain names will be resolved to their true values.')
    parser.add_option('--truedomains', metavar="thesprawl.org,google.com", action="store", help='A comma separated list of domain names which will be resolved to their TRUE values. All other domain names will be resolved to fake values specified in the above parameters.')
    
    rungroup = OptionGroup(parser,"Optional runtime parameters.")
    rungroup.add_option("--nameservers", metavar="8.8.8.8#53 or 2001:4860:4860::8888", default='8.8.8.8', action="store", help='A comma separated list of alternative DNS servers to use with proxied requests. Nameservers can have either IP or IP#PORT format. A randomly selected server from the list will be used for proxy requests when provided with multiple servers. By default, the tool uses Google\'s public DNS server 8.8.8.8 when running in IPv4 mode and 2001:4860:4860::8888 when running in IPv6 mode.')
    rungroup.add_option("-i","--interface", metavar="127.0.0.1 or ::1", default="127.0.0.1", action="store", help='Define an interface to use for the DNS listener. By default, the tool uses 127.0.0.1 for IPv4 mode and ::1 for IPv6 mode.')
    rungroup.add_option("-t","--tcp", action="store_true", default=False, help="Use TCP DNS proxy instead of the default UDP.")
    rungroup.add_option("-6","--ipv6", action="store_true", default=False, help="Run in IPv6 mode.")
    rungroup.add_option("-p","--port", action="store", metavar="53", default="53", help='Port number to listen for DNS requests.')
    rungroup.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True, help="Don't show headers.")
    parser.add_option_group(rungroup)

    (options,args) = parser.parse_args(argv)
 
    # Print program header
    if options.verbose:
        print header
    
    # Main storage of domain filters
    # NOTE: RDMAP is a dictionary map of qtype strings to handling classses
    nametodns = dict()
    for qtype in RDMAP.keys():
        nametodns[qtype] = dict()
    
    # Incorrect or incomplete command line arguments
    if options.fakedomains and options.truedomains:
        print "[!] You can not specify both 'fakedomains' and 'truedomains' parameters."
        sys.exit(0)
        
    elif not (options.fakeip or options.fakeipv6) and (options.fakedomains or options.truedomains):
        print "[!] You have forgotten to specify which IP to use for fake responses"
        sys.exit(0)

    # Notify user about alternative listening port
    if options.port != "53":
        print "[*] Listening on an alternative port %s" % options.port

    # Adjust defaults for IPv6
    if options.ipv6:
        print "[*] Using IPv6 mode."
        if options.interface == "127.0.0.1":
            options.interface = "::1"

        if options.nameservers == "8.8.8.8":
            options.nameservers = "2001:4860:4860::8888"

    print "[*] DNSChef started on interface: %s " % options.interface
    
    # Use alternative DNS servers
    if options.nameservers:
        nameservers = options.nameservers.split(',')
        print "[*] Using the following nameservers: %s" % ", ".join(nameservers)

    # External file definitions
    if options.file:
        config = ConfigParser()
        config.read(options.file)
        for section in config.sections():

            if section in nametodns:
                for domain,record in config.items(section):
                    nametodns[section][domain] = record
                    print "[+] Cooking %s replies for domain %s with '%s'" % (section,domain,record)
            else:
                print "[!] DNS Record '%s' is not supported. Ignoring section contents." % section
   
    # DNS Record and Domain Name definitions
    # NOTE: '*.*.*.*.*.*.*.*.*.*' domain is used to match all possible queries.
    if options.fakeip or options.fakeipv6 or options.fakemail or options.fakealias or options.fakens:
        fakeip     = options.fakeip
        fakeipv6   = options.fakeipv6
        fakemail   = options.fakemail
        fakealias  = options.fakealias
        fakens     = options.fakens
        
        if options.fakedomains:
            for domain in options.fakedomains.split(','):

                if fakeip:
                    nametodns["A"][domain.strip()] = fakeip
                    print "[*] Cooking A replies to point to %s matching: %s" % (options.fakeip, ", ".join(nametodns["A"].keys()))

                if fakeipv6:
                    nametodns["AAAA"][domain.strip()] = fakeipv6
                    print "[*] Cooking AAAA replies to point to %s matching: %s" % (options.fakeipv6, ", ".join(nametodns["AAAA"].keys()))

                if fakemail:
                    nametodns["MX"][domain.strip()] = fakemail
                    print "[*] Cooking MX replies to point to %s matching: %s" % (options.fakemail, ", ".join(nametodns["MX"].keys()))

                if fakealias:
                    nametodns["CNAME"][domain.strip()] = fakealias
                    print "[*] Cooking CNAME replies to point to %s matching: %s" % (options.fakealias, ", ".join(nametodns["CNAME"].keys()))

                if fakens:
                    nametodns["NS"][domain.strip()] = fakens
                    print "[*] Cooking NS replies to point to %s matching: %s" % (options.fakens, ", ".join(nametodns["NS"].keys()))
                  
        elif options.truedomains:
            for domain in options.truedomains.split(','):

                if fakeip:
                    nametodns["A"][domain.strip()] = False
                    print "[*] Cooking A replies to point to %s not matching: %s" % (options.fakeip, ", ".join(nametodns["A"].keys()))
                    nametodns["A"]['*.*.*.*.*.*.*.*.*.*'] = fakeip

                if fakeipv6:
                    nametodns["AAAA"][domain.strip()] = False
                    print "[*] Cooking AAAA replies to point to %s not matching: %s" % (options.fakeipv6, ", ".join(nametodns["AAAA"].keys()))
                    nametodns["AAAA"]['*.*.*.*.*.*.*.*.*.*'] = fakeipv6

                if fakemail:
                    nametodns["MX"][domain.strip()] = False
                    print "[*] Cooking MX replies to point to %s not matching: %s" % (options.fakemail, ", ".join(nametodns["MX"].keys()))
                    nametodns["MX"]['*.*.*.*.*.*.*.*.*.*'] = fakemail

                if fakealias:
                    nametodns["CNAME"][domain.strip()] = False
                    print "[*] Cooking CNAME replies to point to %s not matching: %s" % (options.fakealias, ", ".join(nametodns["CNAME"].keys()))
                    nametodns["CNAME"]['*.*.*.*.*.*.*.*.*.*'] = fakealias

                if fakens:
                    nametodns["NS"][domain.strip()] = False
                    print "[*] Cooking NS replies to point to %s not matching: %s" % (options.fakens, ", ".join(nametodns["NS"].keys()))
                    nametodns["NS"]['*.*.*.*.*.*.*.*.*.*'] = fakealias
                  
        else:
            if fakeip:
                nametodns["A"]['*.*.*.*.*.*.*.*.*.*'] = fakeip
                print "[*] Cooking all A replies to point to %s" % fakeip

            if fakeipv6:
                nametodns["AAAA"]['*.*.*.*.*.*.*.*.*.*'] = fakeipv6
                print "[*] Cooking all AAAA replies to point to %s" % fakeipv6

            if fakemail:
                nametodns["MX"]['*.*.*.*.*.*.*.*.*.*'] = fakemail
                print "[*] Cooking all MX replies to point to %s" % fakemail

            if fakealias:
                nametodns["CNAME"]['*.*.*.*.*.*.*.*.*.*'] = fakealias
                print "[*] Cooking all CNAME replies to point to %s" % fakealias

            if fakens:
                nametodns["NS"]['*.*.*.*.*.*.*.*.*.*'] = fakens
                print "[*] Cooking all NS replies to point to %s" % fakens
    
    # Proxy all DNS requests
    if not options.fakeip and not options.fakeipv6 and not options.fakemail and not options.fakealias and not options.fakens and not options.file:
        print "[*] No parameters were specified. Running in full proxy mode"    

    # Launch DNSChef
    start_cooking(interface=options.interface, nametodns=nametodns, nameservers=nameservers, tcp=options.tcp, ipv6=options.ipv6, port=options.port)