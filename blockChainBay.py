#!/home/guest/.local/pipx/venvs/eth-brownie/bin/python

import sys,configparser,argparse,time,subprocess,readline
import urllib.parse
from typing import NamedTuple
from distutils.command.config import config

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

def init():
    active_project = None
    if project.check_for_project():
        active_project = project.load()
        active_project.load_config()
        print(f"{active_project._name} is the active project.")
    from brownie.project.BlockchainbayProject import BlockchainBay
    network.connect()#CONFIG.argv["network"])
    logo()
    global config
    config = configparser.ConfigParser()
    config.read('config.ini')
    config=config['DEFAULT']
    log("Using network %s, account %s" % (config['network'],config['account']) ,"I")
    global t
    t = BlockchainBay.at(config['defaultContractAddress'])
    log("Connected to smart contract at %s" % config['defaultContractAddress'],"I")


def log(message,type):
    print("[%s] %s" % (type,message))

#Test calling the contract
def testContract():
   count=t.getMagnetCount()
   if count==0:
    log("Database reports a total of %d torrents, fill it with something, it's new." % count+1,"W")
   else: log("Database reports a total of %d torrents" % (count+1),"I")

def unpackMagnet(magnet):
    #decode infohash
    infohash=repr(magnet[0])[26:]
    #decode name
    name=b''
    for i in range(2,10):
      name+=bytearray.fromhex(repr(magnet[i])[2:])
    for i in range(len(name)):
      if name[i]==0:
        name=name[:i]
        break
    name=name.decode()
    #decode data
    #packInts="%016X%016X%04X%04X%04X%016X%04X" % (size_bytes,created_unix,seeders,leechers,completed,scraped_date_unix,0)
    size_bytes = int(repr(magnet[1])[2:2+16],base=16)
    created_unix = int(repr(magnet[1])[18:18+16],base=16)
    seeders      = int(repr(magnet[1])[34:34+4],base=16)
    leechers     = int(repr(magnet[1])[38:38+4],base=16)
    completed    = int(repr(magnet[1])[42:42+4],base=16)
    scraped_date_unix = int(repr(magnet[1])[46:46+16],base=16)
    vote         = int(repr(magnet[1])[62:62+4],base=16)
    #return
    return(infohash,name,size_bytes,created_unix,seeders,leechers,completed,scraped_date_unix,vote)

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
  log("Local torrents: %d Remote torrents: %d Need to download: %d" % (localCount+1,remoteCount+1,downloadCount),'I')

  step=100
  for i in range(localCount,remoteCount,step):
      rmax=i+step
      if (rmax>remoteCount): rmax=remoteCount
      log("Downloading %d-%d from %d torrents" % (i,rmax,downloadCount),'I')
      magnets=t.getMagnets(i,rmax)
      f=open(cachefile,"a")
      for m in magnets:
        data = unpackMagnet(m[0])
        line="%s;%s;%d;%d;%d;%d;%d;%d;%d\n" % (data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7],data[8])
        f.write(line)
        # Add magnet to cache
        infohash=data[0]
        name=data[1]
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
  log('Sync done. Loaded torrents: %d' % (len(cache)+1),'I')

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
      Id=int(cmd.split(' ')[1])
      magnet=t.getMagnet(Id)
      mdata=unpackMagnet(magnet)
      print(mdata[0], mdata[1], mdata[2], mdata[3], mdata[4], mdata[5], mdata[6], mdata[7], mdata[8])
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
      magnets=t.getMagnets(i*10,(i*10)+10)
      log("getMagnets (10): %f" % (time.time()-a),'I')

      a=time.time()
      magnets=t.getMagnets(0,100)
      log("getMagnets (100): %f" % (time.time()-a),'I')
      continue

    #--- remote search command
    if cmd.startswith('/remote'):
      word=cmd.split(' ')[1]
      mcount=t.getMagnetCount()
      step=50
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
          data=unpackMagnet(magnet)
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
          ColorPrint.print_info("[%d]: %s size:%d bytes seeders:%d leechers:%d" % (fcount,m.name.decode(),m.size_bytes,m.seeders,m.leechers))
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
      i=unpackMagnet(magnet)
      print("\n")
      print("%s size:%d bytes seeders:%d leechers:%d" % (i[1],i[2],i[4],i[5]))
      a=input('About to vote up that torrent, proceed (y/n)?')
      if (a.lower()=='y'):
        account = accounts[0]
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


    #---Do search of substings
    if len(cmd)>2:
      searchResults.clear()
      fcount=0
      for i in cache:
        if i.name.find(cmd.encode('utf-8'))>=0:
          fcount+=1
          ColorPrint.print_pass("[%d]: %s size:%d bytes seeders:%d leechers:%d" % (fcount,i.name.decode(),i.size_bytes,i.seeders,i.leechers))
          searchResults.append(i)

#--- Pack magnet into bytes32 array
def pack(infohash,name,size_bytes,created_unix,seeders,leechers,completed,scraped_date_unix,maxNameLenght=256):
    ret=[]
    #convert infohash to bytes32
    ihash=convert.to_bytes(infohash.decode(),"bytes32")
    ret.append(ihash)
    #convert integers to bytes32
    packInts="%016X%016X%04X%04X%04X%016X%04X" % (size_bytes,created_unix,seeders,leechers,completed,scraped_date_unix,0)
    ints=convert.to_bytes(packInts,"bytes32")
    ret.append(ints)
    #compress and convert name to bytes32 array
    #name=zlib.compress(name)
    pad=b'\x00'*(((int(len(name)/32))+1)*32-len(name))
    name=name+pad
    if len(name)>maxNameLenght:
        print("Title (%d bytes) Too big (max %d bytes)." % (len(name),maxNameLenght))
        exit(-1)
    hexname=name.hex()
    for i in range(0,len(hexname),64):
        iname=convert.to_bytes(hexname[i:i+64],"bytes32")
        ret.append(iname)
    return ret

#--- Sends packed magnet to smart contract for publication
def publish(infohash,name,size_bytes,created_unix,seeders,leechers,completed,scraped_date_unix):
    size_bytes=int(size_bytes)
    created_unix=int(created_unix)
    seeders=int(seeders)
    leechers=int(leechers)
    completed=int(completed)
    scraped_date_unix=int(scraped_date_unix)
    dataString="%s;%s;%s;%s;%s;%s;%s;%s" % (infohash,name,size_bytes,created_unix,seeders,leechers,completed,scraped_date_unix)
    packedData=pack(infohash,name,size_bytes,created_unix,seeders,leechers,completed,scraped_date_unix)

    account = accounts[0]
    #itemId=t.createAscii(dataString,{'from': account}).return_value
    #print("Torrent created successfully. Id is %d" % itemId)
    itemId=t.createMagnet(packedData,{'from': account}).return_value
    print("Magnet created successfully. Id is %d" % itemId)

   # datarray=[]
   # for i in range(10):datarray.append(packedData)
   # itemId=t.createMagnet10(datarray,{'from': account}).return_value
   # print("Item3 created successfully. Id is %d" % itemId)

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
      for t in torrents:
        publish(t[0],t[1],t[2],t[3],t[4],t[5],t[6],t[7])
      exit(0)

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

