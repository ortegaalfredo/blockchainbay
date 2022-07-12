#!/usr/bin/python3

import sys,configparser,argparse,time,subprocess,readline,os
import urllib.parse
from typing import NamedTuple

from brownie import accounts,network,project,convert

# Print logo
def logo():
    print("""
    ____________________________
  /|............................|
 | |:       BlockChain Bay     :|
 | |:           V1.0           :|
 | |:     ,-.   _____   ,-.    :|
 | |:    ( `)) [_____] ( `))   :|
 |v|:     `-`   ' ' '   `-`    :|
 |||:     ,______________.     :|
 |||...../::::o::::::o::::\.....|
 |^|..../:::O::::::::::O:::\....|
 |/`---/--------------------`---|
 `.___/ /====/ /=//=/ /====/____/
      `--------------------'

    """)

#magnet cache
cache=[]

#This class handles the Magnet storage and packing/unpacking to bytes32 format
class Magnet(NamedTuple):
  infohash:str
  name:str
  size_bytes:int
  created_unix:int
  seeders:int
  leechers:int
  completed:int
  scraped_date_unix:int
  vote:int

  # Convert from magnet bytes32 packed data to torrent variables
  @staticmethod
  def unpackMagnet(bytes32magnet):
      #decode infohash
      infohash=repr(bytes32magnet[0])[26:]
      #decode name
      name=b''
      for i in range(2,10):
        name+=bytearray.fromhex(repr(bytes32magnet[i])[2:])
      for i in range(len(name)):
        if name[i]==0:
          name=name[:i]
          break
      name=name.decode()
      #decode data
      size_bytes = int(repr(bytes32magnet[1])[2:2+16],base=16)
      created_unix = int(repr(bytes32magnet[1])[18:18+16],base=16)
      seeders      = int(repr(bytes32magnet[1])[34:34+4],base=16)
      leechers     = int(repr(bytes32magnet[1])[38:38+4],base=16)
      completed    = int(repr(bytes32magnet[1])[42:42+4],base=16)
      scraped_date_unix = int(repr(bytes32magnet[1])[46:46+16],base=16)
      vote         = int(repr(bytes32magnet[1])[62:62+4],base=16)
      return(infohash,name,size_bytes,created_unix,seeders,leechers,completed,scraped_date_unix,vote)
  #--- Pack magnet into bytes32 array
  def packMagnet(self,maxNameLenght=256):
      ret=[]
      initialVotes=0
      #convert infohash to bytes32
      ihash=convert.to_bytes(self.infohash.decode(),"bytes32")
      ret.append(ihash)
      #convert integers to bytes32
      packInts="%016X%016X%04X%04X%04X%016X%04X" % (self.size_bytes,self.created_unix,self.seeders,self.leechers,self.completed,self.scraped_date_unix,initialVotes)
      ints=convert.to_bytes(packInts,"bytes32")
      ret.append(ints)
      #compress and convert name to bytes32 array
      #name=zlib.compress(name) # cannot use search if we compress on the server
      pad=b'\x00'*(((int(len(self.name)/32))+1)*32-len(self.name))
      pname=self.name+pad
      if len(pname)>maxNameLenght:
          print("Title (%d bytes) Too big (max %d bytes)." % (len(pname),maxNameLenght))
          exit(-1)
      hexname=pname.hex()
      for i in range(0,len(hexname),64):
          iname=convert.to_bytes(hexname[i:i+64],"bytes32")
          ret.append(iname)
      return ret

# pretty-print
class ColorPrint:

    @staticmethod
    def print_fail(message, end = '\n'):
        sys.stderr.write('\x1b[1;31m' + message.strip() + '\x1b[0m' + end)

    @staticmethod
    def print_pass(message, end = '\n'):
        sys.stdout.write('\x1b[1;32m' + message.strip() + '\x1b[0m' + end)

    @staticmethod
    def print_warn(message, end = '\n'):
        sys.stderr.write('\x1b[1;33m' + message.strip() + '\x1b[0m' + end)

    @staticmethod
    def print_info(message, end = '\n'):
        sys.stdout.write('\x1b[1;34m' + message.strip() + '\x1b[0m' + end)

    @staticmethod
    def print_bold(message, end = '\n'):
        sys.stdout.write('\x1b[1;37m' + message.strip() + '\x1b[0m' + end)

# Simple logging
def log(message,type):
    print("[%s] %s" % (type,message))

# Network, account and smart contract initialization
def init():
    active_project = None
    if project.check_for_project():
        active_project = project.load()
        active_project.load_config()
    from brownie.project.BlockchainbayProject import BlockchainBay
    global config
    config = configparser.ConfigParser()
    config.read('config.ini')
    config=config['DEFAULT']
    log("Using network %s, account %s" % (config['network'],config['account']) ,"I")
    global t
    global account
    try:
      network.connect(config['network'])
    except:
      log("Error connecting to network, try adding network and account to brownie in this way:","E")
      print("\n\tbrownie networks modify polygon-main host=https://rpc.ankr.com/polygon")
      exit(0)
    try:
      account = accounts.load(config['account'],password=config['accountpass'])
    except:
      log("Error connecting to account, try generating an account in this way:","E")
      print("\n\tbrownie accounts generate %s" % config['account'])
      exit(0)

    t = BlockchainBay.at(config['defaultContractAddress'])
    log("Connected to smart contract at %s" % config['defaultContractAddress'],"I")
    logo()


#Test calling the contract
def testContract():
   count=t.getMagnetCount()
   if count==0:
    log("Database reports a total of %d torrents, fill it with something, it's new." % (count),"W")
   else: log("Database reports a total of %d torrents" % (count),"I")

# Download torrents to local cache file
def sync():
  global cache
  cache=[]
  localCount=0
  cachefile = config['cachefile']
  remoteCount=t.getMagnetCount()
  try:
    a=open(cachefile,"rb")
    for l in a.readlines():
      localCount=localCount+1
      l=l.split(b';')
      # Add line to cache
      infohash=l[0]
      name=l[1]
      size_bytes=int(l[2])
      created_unix=int(l[3])
      seeders=int(l[4])
      leechers=int(l[5])
      completed=int(l[6])
      scraped_date_unix=int(l[7])
      vote=int(l[8])
      m = Magnet(infohash,name,size_bytes,created_unix,seeders,leechers,completed,scraped_date_unix,vote)
      cache.append(m)
    a.close()
  except:
    log('Cache file not found, creating it..','E')
    pass
  downloadCount=remoteCount-localCount  
  log("Local torrents: %d Remote torrents: %d Need to download: %d" % (localCount,remoteCount,downloadCount),'I')

  step=500
  for i in range(localCount,remoteCount,step):
      rmax=i+step
      if (rmax>remoteCount): rmax=remoteCount
      log("Downloading %d-%d from %d torrents" % (i,rmax,downloadCount),'I')
      magnets=t.getMagnets(i,rmax)
      f=open(cachefile,"a")
      for m in magnets:
        data = Magnet.unpackMagnet(m[0])
        line="%s;%s;%d;%d;%d;%d;%d;%d;%d\n" % (data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7],data[8])
        f.write(line)
        # Add magnet to cache
        infohash=data[0].encode('utf-8')
        name=data[1].encode('utf-8')
        size_bytes=int(data[2])
        created_unix=int(data[3])
        seeders=int(data[4])
        leechers=int(data[5])
        completed=int(data[6])
        scraped_date_unix=int(data[7])
        vote=int(data[8])
        m = Magnet(infohash,name,size_bytes,created_unix,seeders,leechers,completed,scraped_date_unix,vote)
        cache.append(m)
      f.close()
  log('Sync done. Loaded torrents: %d' % (len(cache)),'I')

def main():
   global searchResults
   searchResults=[]
   while(True):
    cmd=input('Enter search term: ')
    #--- quit command
    if cmd.startswith('/quit'):
      exit(0)

    #--- getid command
    if cmd.startswith('/getid '):
      try:
        Id=int(cmd.split(' ')[1])
        magnet=t.getMagnet(Id)
        mdata=Magnet.unpackMagnet(magnet)
        print(mdata[0], mdata[1], mdata[2], mdata[3], mdata[4], mdata[5], mdata[6], mdata[7], mdata[8])
      except:
        log("Error: id non existent","E")
        pass
      continue

    #--- Benchmark command
    if cmd.startswith('/benchmark'):
      log("Performing Benchmark....",'I')
      a=time.time()
      (count,magnets)=t.searchMagnet(0,10,b"mp4")
      log("searchMagnet (10): %f" %(time.time()-a),'I')

      a=time.time()
      (count,magnets)=t.searchMagnet(0,100,b"mp4")
      log("searchMagnet (100): %f" %(time.time()-a),'I')
      
      a=time.time()
      (count,magnets)=t.searchMagnet(0,400,b"mp4")
      log("searchMagnet (400): %f" %(time.time()-a),'I')
      
      a=time.time()
      magnets=t.getMagnets(0,10)
      log("getMagnets (10): %f" % (time.time()-a),'I')

      a=time.time()
      magnets=t.getMagnets(0,100)
      log("getMagnets (100): %f" % (time.time()-a),'I')
      continue

    #--- remote search command
    if cmd.startswith('/remote'):
      word=cmd.split(' ')[1]
      mcount=t.getMagnetCount()
      step=100
      searchResults.clear()
      fcount=0
      for i in range(0,mcount,step):
        smin=i
        smax=i+step
        if (smax>mcount): smax=mcount
        log('Searching remotely for "%s" on %d-%d from %d torrents' % (word,smin,smax,mcount),'I')
        (count,magnets)=t.searchMagnet(smin,smax,word.encode('utf-8'))
        for i in range(count):
          magnet=magnets[i][0]
          data=Magnet.unpackMagnet(magnet)
          # Add magnet to search results
          infohash=data[0].encode('utf-8')
          name=data[1].encode(('utf-8'))
          size_bytes=int(data[2])
          created_unix=int(data[3])
          seeders=int(data[4])
          leechers=int(data[5])
          completed=int(data[6])
          scraped_date_unix=int(data[7])
          vote=int(data[8])
          m = Magnet(infohash,name,size_bytes,created_unix,seeders,leechers,completed,scraped_date_unix,vote)
          fcount+=1
          ColorPrint.print_info("[%d]: %s size:%d bytes seeders:%d leechers:%d votes: %d" % (fcount,m.name.decode(),m.size_bytes,m.seeders,m.leechers,m.vote))
          searchResults.append(m)
      log('Done.','I')
      continue

    #---sync command: Downloads recent torrents
    if cmd.startswith('/sync'):
      sync()
      continue

    #---link command: prints magnet link of search result
    if cmd.startswith('/link'):
      Id=int(cmd.split(' ')[1])
      if (Id>len(searchResults)) or (Id<=0):
        log("Search result not found.",'E')
        continue
      i=searchResults[Id-1]
      print("\n")
      print("%s size:%d bytes seeders:%d leechers:%d" % (i.name.decode(),i.size_bytes,i.seeders,i.leechers))
      print("\n")
      ColorPrint.print_info(config['link'] % (urllib.parse.quote(i.infohash.decode()),urllib.parse.quote(i.name.decode())))
      print("\n")
      continue

    #--- Download using configured bittorrent client
    if cmd.startswith('/download'):
      Id=int(cmd.split(' ')[1])
      if (Id>len(searchResults)) or (Id<=0):
        log("Search result not found.",'E')
        continue
      i=searchResults[Id-1]
      magnetlink=config['link'] % (urllib.parse.quote(i.infohash),urllib.parse.quote(i.name))
      subprocess.run([config['bittorrent-client'],magnetlink])
      continue

    #--- Vote for a particular torrent ID      
    if cmd.startswith('/vote'):
      Id=int(cmd.split(' ')[1])
      magnet=t.getMagnet(Id)
      i=Magnet.unpackMagnet(magnet)
      print("\n")
      print("%s size:%d bytes seeders:%d leechers:%d" % (i[1],i[2],i[4],i[5]))
      a=input('About to vote up that torrent, proceed (y/n)?')
      if (a.lower()=='y'):
        #account = accounts.load(config['account'],password=config['accountpass'])
        t.vote(Id,{'from': account})
      log('Done.','I')
      continue

    #--- print commands help
    if cmd.startswith('/help'):
      print("""
Available commands:
      /quit          :Exit to shell
      /getid <n>     :Show the torrent n in the remote database
      /remote <str>  :Search for <str> in the remote database
      /sync          :Downloads all torrents to the cache file
      /link <n>      :Obtain link from search result
      /download <n>  :Launch bittorrent client on search result
      /vote <n>      :Vote torrent up (Warning: consumes balance from account)
      /benchmark     :Perform simple query benchmark
      /help          :Print help
      <string>       :Search for string in the local torrent cache
      """)


    #---Do cached search of substings
    if len(cmd)>2:
      searchResults.clear()
      fcount=0
      for i in cache:
        try:
          if i.name.lower().find(cmd.lower().encode('utf-8'))>=0:
            fcount+=1
            ColorPrint.print_pass("[%d]: %s size:%d bytes seeders:%d leechers:%d votes: %d" % (fcount,i.name.decode(),i.size_bytes,i.seeders,i.leechers,i.vote))
            searchResults.append(i)
        except Exception as e:
            log("Error while searching","E")
            log(e,"E")
            pass

#Load torrent database for publication
def loadFile(file):
  torrents=[]
  a=open(file,'rb')
  for l in a.readlines():
    if l.startswith(b'#'):
      continue
    ls=l.split(b';')
    torrents.append(ls)
  return torrents

# Command-line argument parser
# Used mostly as the torrent upload tool

def argparser():
  parser = argparse.ArgumentParser(description='EVM Bittorrent distribution tool, (C) Cybergaucho 2022 @ortegaalfredo')
  parser.add_argument('--upload', type=str,required=False,help='Upload torrent from file')
  args = parser.parse_args()
  if args.upload:
    log('Loading file %s' % args.upload,'I')
    torrents=loadFile(args.upload)
    a=input('About to upload %d torrents, proceed (y/n)?' % len(torrents))
    if (a.lower()=='y'):
      init()
      packedMagnets=[]
      mcount=0
      for q in torrents:
        try:
          mcount+=1
          m = Magnet(q[0],q[1],int(q[2]),int(q[3]),int(q[4]),int(q[5]),int(q[6]),int(q[7]),0)
          #packedMagnets.append(packMagnet(q[0],q[1],int(q[2]),int(q[3]),int(q[4]),int(q[5]),int(q[6]),int(q[7])))
          packedMagnets.append(m.packMagnet())# packMagnet(q[0],q[1],int(q[2]),int(q[3]),int(q[4]),int(q[5]),int(q[6]),int(q[7])))
          # publish blocks of 10 torrents
          if len(packedMagnets)==10:
              try:
                itemId=t.createMagnet10(packedMagnets,{'from': account}).return_value
                print("Magnets created successfully. Id is %d" % itemId)
              except Exception as e:
                log(e,"E")
              print("Sent Magnets %d to %d" % (mcount-10,mcount))
              packedMagnets=[]
        except Exception as e:
            log(e,"E")
            pass
      # send remaining torrents
      for i in packedMagnets:
        try:
          itemId=t.createMagnet(i,{'from': account}).return_value
          print("Magnet created successfully. Id is %d" % itemId)
        except Exception as e:
          log(e,"E")
          pass


      exit(0)

#readline auto-complete of commands
def complete(text,state):
    volcab = ['/help','/getid','/remote','/sync','/link','/download','/vote','/benchmark']
    results = [x for x in volcab if x.startswith(text)] + [None]
    return results[state]

if __name__ == '__main__':
   readline.parse_and_bind("tab: complete")
   delims = readline.get_completer_delims()
   readline.set_completer_delims(delims.replace('/', ''))
   readline.set_completer(complete)
   argparser()
   init()
   testContract()
   sync()
   main()