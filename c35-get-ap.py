
from netmiko import ConnectHandler
import sys
import getpass
import os
import re
import subprocess
from pprint import pprint
import argparse


##
# Connects to and queries the C35 controller
##
class c35_connection( object ):
    def __init__(self,connection_info):
        self.connection_info = connection_info
        self.ssh = ConnectHandler(**connection_info)
        self.uptime = self.run_cmd('show system_state uptime')
        self.aps = self.get_all_aps()

    @staticmethod
    def get_ap_fields():
        return c35_connection.AP_Info.get_field_names()
    @staticmethod
    def get_client_fields():
        return c35_connection.Client_Info.get_field_names()

    def run_cmd( self, cmd ):
        if self.ssh.find_prompt():
            result = self.ssh.send_command(cmd)
            return result
        else:
            raise "Can't find prompt!"

    def get_all_aps(self):
        aps = []
        # Usage: show ap
        #   [
        #       access | registration | version | load-groups
        #       | (defaults [config | standard | 11n | dualband | 4102 | ap37xx | ap38xx | ap3801])
        #       | (<ap_serial>  [clients | static_config | config | radio1 | radio2 | version | professional_antenna])
        #   ]
        result = self.run_cmd( 'show ap' ) #serial 0000142145195600 es-frontyard-wap AP3765i\n...
        lines = result.split('\n')
        linere = re.compile( r'^serial\s+(\S+)\s+(\S+)\s+(\S+)' )
        for line in lines:
            r = re.search( linere, line)
            if r:
                ap = c35_connection.AP_Info()
                ap.name = r.group(2)
                ap.serial = r.group(1)
                ap.model = r.group(3)
                aps.append( ap )
        return aps

    def print_c35_info(self):
        print( self.uptime )


    def get_ap_info( self, ap ):
        #if serial and hostname:
        #     raise Exception('Call to get_ap_info() can not use both "serial" and "hostname" parameters')
        # if serial:
        #     ap = self.get_ap_by_serial( serial )
        # else if hostname:
        #     ap = self.get_ap_by_name( name )

        #info  = {}

        # # show ap 14025683915R0000 config
        # AP Serial Number: 14025683915R0000
        # AP host name: co-southwest-wap
        # AP Name: co-southwest-wap
        # Description:
        # Active # of clients: 23
        # AP software version: 09.21.19.0003
        # Status: approved
        # role : ap
        # Home: local
        # Static IP address: 10.4.2.12
        # Static NetMask: 255.255.255.0
        # Static Gateway: 10.4.2.1
        # Hardware Type: Wireless AP3705i Internal
        # Wired MAC address: 20:B3:99:BB:58:70
        result = self.run_cmd( 'show ap %s config'%(ap.serial) )
        lines = result.split('\n')
        for line in lines:
            r = re.match('([^:]+): (.*)',line)
            if r:
                name = r.group(1)
                value = r.group(2)
                if name == 'Description': ap.descr = value
                if name == 'Active # of clients': ap.client_count = value
                if name == 'AP software version': ap.version = value
                if name == 'Status': ap.status = value
                if name == 'role': ap.role = value
                if name == 'Home': ap.home = value
                if name == 'Static IP address': ap.ip = value
                if name == 'Static NetMask': ap.mask = value
                if name == 'Static Gateway': ap.gateway = value
                if name == 'Hardware Type': ap.model = value
                if name == 'Wired MAC address': ap.mac = value
                # assuming "show ap" shows host names
                #if name == 'AP host name': infohostname = value
                if name == 'AP Name': ap.friendly_name = value
        return ap

    def get_clients_by_ap( self, ap,bssid='', ssid='',proto='',mac='',ip=''):
        output = self.run_cmd( 'show clients apserial {}'.format( ap.serial ) )
        #Client IP   Client MAC         Protocol  Radio  BSS MAC            SSID              Aut./Priv.  Time Conn.  User  Roamed  Role          Default Action  PVID          RSS(dBm)  Avg.Rate(Mbps) Sent/Recvd  Packets Sent/Recvd  Bytes Sent/Recvd  UL Drop Rate Packets/Bytes  DL Drop Rate Packets/Bytes  DL Drop Buffer Packets/Bytes
        #10.1.3.95   54:72:4F:CF:DC:CD  5.0n      1      00:1B:1B:A0:98:61  Free Co-op Wi-Fi  None/None   00:38:51    -     NO      RoleFreeWiFi                  TopoFreeWiFi  -78       0/24.0                     561/3160            316505/141995     0/0                         0/0                         0/0
        clp = c35_connection.ClientListParser( output )
        client_list = []
        for client in clp.clients:
            c = c35_connection.Client_Info()
            c.ap = ap.name
            c.ip = client[0]
            c.mac = client[1]
            c.proto = client[2]
            c.bssid = client[4]
            c.ssid = client[5]

            if bssid and bssid != c.bssid:
                continue
            if ssid  and ssid != c.ssid:
                continue
            if proto  and proto != c.proto:
                continue
            if mac  and mac != c.mac:
                continue
            if ip and ip != c.ip:
                continue

            c.radio = client[3]
            c.authpriv = client[6]
            c.conntime = client[7]
            c.user = client[8]
            c.roamed = client[9]
            c.role = client[10]
            c.defaultaction = client[11]
            c.pvid = client[12]
            c.rss = client[13]
            c.avgratesr = client[14]
            c.packetssr = client[15]
            c.bytessr = client[16]
            c.uldropratepkby = client[17]
            c.dldropratepkby = client[18]
            c.dldropbufpkby  =  client[19]

            client_list.append(c)
        return client_list

       # clients = clp.clients
       # client_list = []
       # for client in clients:
       #     cdict = {}
       #     cdict['ap'] = ap.name
       #     cdict['ip'] = client[0]
       #     cdict['mac'] = client[1]
       #     cdict['proto'] = client[2]
       #     cdict['radio'] = client[3]
       #     cdict['bssid'] = client[4]
       #     cdict['ssid'] = client[5]
       #     cdict['authpriv'] = client[6]
       #     cdict['conntime'] = client[7]
       #     cdict['user'] = client[8]
       #     cdict['roamed'] = client[9]
       #     cdict['role'] = client[10]
       #     cdict['defaultaction'] = client[11]
       #     cdict['pvid'] = client[12]
       #     cdict['rss'] = client[13]
       #     cdict['avgratesr'] = client[14]
       #     cdict['packetssr'] = client[15]
       #     cdict['bytessr'] = client[16]
       #     cdict['uldropratepkby'] = client[17]
       #     cdict['dldropratepkby'] = client[18]
       #     cdict['dldropbufpkby']  =  client[19]
       #     if bssid and bssid != cdict['bssid']:
       #         continue
       #     if ssid  and ssid != cdict['ssid']:
       #         continue
       #     if proto  and proto != cdict['proto']:
       #         continue
       #     if mac  and mac != cdict['mac']:
       #         continue
       #     if ip and ip != cdict['ip']:
       #         continue
       #     client_list.append(cdict)
       # return client_list

    def get_clients_by_ap_name(self,name,bssid='', ssid='',proto='',mac='',ip='',):
       ap = self.get_ap_by_name( name )
       return self.get_clients_by_ap( ap ,bssid, ssid,proto,mac,ip)

    def get_clients( self, aps=[],bssid='', ssid='', proto='',mac='',ip='' ):
        clients = []
        for ap in aps:
            c = self.get_ap_clients(ap.name,bssid,ssid,proto,mac,ip)
            clients.append(c)


    def get_ap_by_serial(self,serial):
        for ap in self.aps:
            if ap.serial == serial:
                return ap

    def get_ap_by_name(self,name):
        for ap in self.aps:
            if ap.name == name:
                return ap

    def get_aps_by_regex(self,regex):
        aps = []
        for ap in self.aps:
            if re.search(regex,ap.name,re.I):
                aps.append( ap )
        return aps

    def get_ap_client_by_mac( self, mac,aps):
        found = []
        for ap in aps:
            clients = get_ap_clients(self,name,mac=mac)
            found.append( clients )
        return  found
    ##
    # Parses the fixed width field AP client information
    ##
    class ClientListParser( object ):
        headers = [
            'Client IP'
            ,'Client MAC'
            ,'Protocol'
            ,'Radio'
            ,'BSS MAC'
            ,'SSID'
            ,'Aut./Priv.'
            ,'Time Conn.'
            ,'User'
            ,'Roamed'
            ,'Role'
            ,'Default Action'
            ,'PVID'
            ,'RSS(dBm)'
            ,'Avg.Rate(Mbps) Sent/Recvd'
            ,'Packets Sent/Recvd'
            ,'Bytes Sent/Recvd'
            ,'UL Drop Rate Packets/Bytes'
            ,'DL Drop Rate Packets/Bytes'
            ,'DL Drop Buffer Packets/Bytes'
            ]
        ## data = list of lines from 'show ap ... clients'
        def __init__(self, rawdata):
            self.data = rawdata.split('\n')
            widths = []
            clients = []
            for line in self.data:
                if re.match('\s*$', line):
                    continue
                if re.match( re.escape( self.headers[0] ) , line):
                    widths = self.get_field_widths( line )
                    continue
                if re.match('Total',line):
                    continue
                pos = 0
                client = []
                for i in range(len(widths)):
                    end = pos + widths[i]
                    f = line[pos:end]
                    client.append( f.rstrip() )
                    pos=pos+widths[i]
                clients.append(client)
            if len(widths) == 0:
                raise Exception('Unable to calculate field widths from client list!')
            self.clients = clients

        def get_field_widths(self, headerline):
            widths = []
            hl = len(self.headers)
            for i in range(hl):
                regex1 = re.escape( self.headers[i] )
                if i == (hl-1):
                    regex2 = '$'
                else:
                    regex2 = re.escape( self.headers[i+1] )
                regex = '(' + regex1 + '\s*)'+regex2
                r = re.search(regex, headerline )
                field_width = len(r.group(1))
                widths.append( field_width )
            return widths


    ##
    # Encapsulates AP Information
    ##
    class AP_Info( object ):
        vaps = {}
        ip = ''
        name = ''
        serial = ''
        descr = ''
        model = ''
        client_count = ''
        version = ''
        status = ''
        role = ''
        home = ''
        mask = ''
        gateway = ''
        mac = ''
        hostname = ''
        friendly_name = ''

        @staticmethod
        def get_field_names():
            names = []
            for attribute in c35_connection.AP_Info.__dict__.keys():
                if attribute[:2] != '__':
                    value = getattr(c35_connection.AP_Info, attribute)
                    if not callable(value):
                        names.append(attribute)
            return names

    class Client_Info(object):
        ap = ''
        ip = ''
        mac = ''
        proto = ''
        radio = ''
        bssid = ''
        ssid = ''
        authpriv = ''
        conntime = ''
        user = ''
        roamed = ''
        role = ''
        defaultaction = ''
        pvid = ''
        rss = ''
        avgratesr = ''
        packetssr = ''
        bytessr = ''
        uldropratepkby = ''
        dldropratepkby = ''
        dldropbufpkby = ''
        @staticmethod
        def get_field_names():
            names = []
            for attribute in c35_connection.Client_Info.__dict__.keys():
                if attribute[:2] != '__':
                    value = getattr(c35_connection.Client_Info, attribute)
                    if not callable(value):
                        names.append(attribute)
            return names


def format_dict( format_str, dict, keys):
    return format_str.format( *tuple(dict[key] for key in keys))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='c35-get-ap-')

    parser.add_argument('--server', '-s', action='store',required=True)

    group = parser.add_mutually_exclusive_group( required=True )
    group.add_argument('--sn', action='store')
    group.add_argument('--apname', '-n', action='store')
    group.add_argument('--hostregex', '-r', action='store')
    group.add_argument('--all', '-a', action='store_true')

    parser.add_argument('--bssid', '-b',  action='store') # only used for client lists
    parser.add_argument('--ssid', '-i', action='store') # only used for client lists
    parser.add_argument('--proto', '-p', action='store') # only used for client lists

    parser.add_argument('--format', '-f', action='store')
    parser.add_argument('--delim', '-d', action='store')
    parser.add_argument('--clients', '-c', action='store_true')
    args = parser.parse_args()

    if args.format and args.format.lower() == 'help':
        if args.clients:
            print('Available fields for client lists:')
            print( ', '.join( c35_connection.get_client_fields() ) )
            exit(0)
        else:
            print('Available fields for AP lists:')
            print( ', '.join( c35_connection.get_ap_fields() ) )
            exit(0)

    usern = ''
    passw = ''
    if 'NM_USER' in os.environ:
      usern = os.environ['NM_USER']
    if 'NM_PASS' in os.environ:
      passw = os.environ['NM_PASS']

    if not usern and not passw:
      usern = input("Username [%s]: " % getpass.getuser())
      if not usern:
        usern = getpass.getuser()
      passw = getpass.getpass()

    c35 = c35_connection( { 'verbose':False,'global_delay_factor':.5,'device_type': 'enterasys','ip': args.server,'username': usern,'password': passw } )

    if False: #args.clients :
        if args.format:
            format=args.format
        else:
            format = 'ip,mac,ssid,rss'
        if args.delim:
            delim = args.delim
        else:
            delim = '\t'
        fields = format.split(',')
        clients = c35.get_ap_clients('ws-office-wap', ssid=args.ssid, bssid=args.bssid,proto=args.proto)

        for client in clients:
            c = []
            for field in fields:
                c.append( client[field] )
            print( delim.join(c) )
    else:
        # FIXME no need to get ap_extended info when getting client list

        if args.apname:
            ap_infos = [c35.get_ap_by_name( args.apname )]
        elif args.sn:
            ap_infos = [c35.get_ap_by_serial( args.sn )]
        elif args.hostregex:
            ap_infos = c35.get_aps_by_regex( args.hostregex )
        elif args.all:
            ap_infos = c35.aps

        if args.clients:
            if args.format:
               format=args.format
            else:
               format = 'ip,mac,ap,ssid,rss'
            if args.delim:
               delim = args.delim
            else:
               delim = '\t'
            fields = format.split(',')
            for ap_info in ap_infos:
                clients = c35.get_clients_by_ap( ap_info,ssid=args.ssid, bssid=args.bssid,proto=args.proto)
                for client in clients:
                   c = []
                   for field in fields:
                       c.append( getattr(client,field ))
                   print( delim.join(c) )
        else:
            if args.format:
                format=args.format
            else:
                format = 'name,version,ip,model'
            if args.delim:
                delim = args.delim
            else:
                delim = '\t'
            fields = format.split(',')
            for ap_info in ap_infos:
                a=[]
                ap = c35.get_ap_info( ap_info )
                for field in fields:
                    a.append( getattr( ap, field ) )
                print( delim.join(a) )
