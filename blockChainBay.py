#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys,configparser,argparse,time,subprocess,os
import urllib.parse
from typing import NamedTuple
from web3 import Web3
from web3.middleware import geth_poa_middleware
import platform

import collections
collections.Callable=collections.abc.Callable

try:
    import readline
except:
    from pyreadline import Readline
    readline=Readline()
    pass

# Print logo
def logo():
    print("""
    ____________________________
  /|............................|
 | |:       BlockChain Bay     :|
 | |:   V1.1 'Fuck Metallica'  :|
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
      infohash=bytes32magnet[0][12:].hex()
      #decode name
      name=b''
      for i in range(2,10):
        name+=bytes32magnet[i]
      name=name.decode('utf-8').strip('\x00')
      #decode data
      size_bytes = int.from_bytes(bytes32magnet[1][0:8],"big",signed=False)
      created_unix = int.from_bytes(bytes32magnet[1][8:8+8],"big",signed=False)
      seeders      = int.from_bytes(bytes32magnet[1][16:16+2],"big",signed=False)
      leechers     = int.from_bytes(bytes32magnet[1][18:18+2],"big",signed=False)
      completed    = int.from_bytes(bytes32magnet[1][20:20+2],"big",signed=False)
      scraped_date_unix = int.from_bytes(bytes32magnet[1][22:22+8],"big",signed=False)
      vote         = int.from_bytes(bytes32magnet[1][30:30+2],"big",signed=False)
      return(infohash,name,size_bytes,created_unix,seeders,leechers,completed,scraped_date_unix,vote)
  #--- Pack magnet into bytes32 array
  def packMagnet(self,maxNameLenght=256):
      ret=[]
      initialVotes=0
      #convert infohash to bytes32
      ihash=bytes.fromhex(self.infohash.decode())
      #pad with 0x00
      ihash=(b'\x00'*(32-len(ihash)))+ihash
      ret.append(ihash)
      #convert integers to bytes32
      packInts="%016X%016X%04X%04X%04X%016X%04X" % (self.size_bytes,self.created_unix,self.seeders,self.leechers,self.completed,self.scraped_date_unix,initialVotes)
      ints=bytes.fromhex(packInts)
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
          iname=bytes.fromhex(hexname[i:i+64])
          ret.append(iname)
      return ret

# pretty-print
class ColorPrint:

    @staticmethod
    def print_fail(message, end = '\n'):
        if (platform.system()=='Windows'):
              sys.stdout.write(message.strip() + end)
        else: sys.stderr.write('\x1b[1;31m' + message.strip() + '\x1b[0m' + end)

    @staticmethod
    def print_pass(message, end = '\n'):
        if (platform.system()=='Windows'):
              sys.stdout.write(message.strip() + end)
        else: sys.stdout.write('\x1b[1;32m' + message.strip() + '\x1b[0m' + end)

    @staticmethod
    def print_warn(message, end = '\n'):
        if (platform.system()=='Windows'):
              sys.stdout.write(message.strip() + end)
        else: sys.stderr.write('\x1b[1;33m' + message.strip() + '\x1b[0m' + end)

    @staticmethod
    def print_info(message, end = '\n'):
        if (platform.system()=='Windows'):
              sys.stdout.write(message.strip() + end)
        else: sys.stdout.write('\x1b[1;34m' + message.strip() + '\x1b[0m' + end)

    @staticmethod
    def print_bold(message, end = '\n'):
        if (platform.system()=='Windows'):
              sys.stdout.write(message.strip() + end)
        else: sys.stdout.write('\x1b[1;37m' + message.strip() + '\x1b[0m' + end)

# Simple logging
def log(message,type):
    print("[%s] %s" % (type,message))

# Network, account and smart contract initialization
def init():
    global config
    config = configparser.ConfigParser()
    config.read('config.ini')
    config=config['DEFAULT']
    log("Using network %s, account %s" % (config['network'],config['account']) ,"I")
    global web3
    web3=Web3(Web3.HTTPProvider(config['network']))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    log("Is blockchain connected: "+repr(web3.isConnected()),'I')
    logo()
    balance = web3.eth.getBalance(config['account'])
    log("Balance of account %s: %f" % (config['account'],web3.fromWei(balance,'ether')),'I')
    abi=open(config['abi'],'r').read()
    global contract
    contract = web3.eth.contract(address=config['defaultcontractaddress'],abi=abi)
    log("Connected to smart contract at %s" % config['defaultContractAddress'],"I")


#Test calling the contract
def testContract():
   count=contract.functions.getMagnetCount().call()
   if count==0:
    log("Database reports a total of %d torrents, fill it with something, it's new." % (count),"W")
   else: log("Database reports a total of %d torrents" % (count),"I")

# Send transaction and wait for receipt
def sendTransaction(fcall):
          transaction = fcall.buildTransaction({'nonce': web3.eth.get_transaction_count(config["account"])})
          private_key = config['private-key']
          signed_txn = web3.eth.account.signTransaction(transaction, private_key=private_key)
          tx_hash=web3.eth.sendRawTransaction(signed_txn.rawTransaction)
          log("Transaction sent. Id is %s waiting for receipt..." % repr(tx_hash),"I")
          receipt=web3.eth.wait_for_transaction_receipt(tx_hash)
          print("Transaction sent successfully. Receipt:"+repr(receipt.transactionHash.hex()))

# Download torrents to local cache file
def sync():
  global cache
  cache=[]
  localCount=0
  cachefile = config['cachefile']
  remoteCount=contract.functions.getMagnetCount().call()
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
  except Exception as e:
    log('Cache file not found, creating it..','E')
    log(e,"E")
    pass
  downloadCount=remoteCount-localCount
  if (downloadCount<0):
    a=input('Local cache is different than remote. Erase it (y/n)?')
    if (a.lower()=='y'):
      os.remove(cachefile)
      localCount=0
      downloadCount=remoteCount-localCount
  log("Local torrents: %d Remote torrents: %d Need to download: %d" % (localCount,remoteCount,downloadCount),'I')

  step=500
  for i in range(localCount,remoteCount,step):
      rmax=i+step
      if (rmax>remoteCount): rmax=remoteCount
      log("Downloading %d-%d from %d torrents" % (i,rmax,downloadCount),'I')
      try:
        magnets=contract.functions.getMagnets(i,rmax).call()
      except:
        log("Error downloading torrents %d-%d" % (i,rmax),"E")
        continue
      f=open(cachefile,"ab")
      for m in magnets:
        data = Magnet.unpackMagnet(m[0])
        line="%s;%s;%d;%d;%d;%d;%d;%d;%d\n" % (data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7],data[8])
        f.write(line.encode('utf-8'))
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
        magnet=contract.functions.getMagnet(Id).call()
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
      (count,magnets)=contract.functions.searchMagnet(0,10,b"mp4").call()
      log("searchMagnet (10): %f" %(time.time()-a),'I')

      a=time.time()
      (count,magnets)=contract.functions.searchMagnet(0,100,b"mp4").call()
      log("searchMagnet (100): %f" %(time.time()-a),'I')
      
      a=time.time()
      (count,magnets)=contract.functions.searchMagnet(0,400,b"mp4").call()
      log("searchMagnet (400): %f" %(time.time()-a),'I')
      
      a=time.time()
      magnets=contract.functions.getMagnets(0,10).call()
      log("getMagnets (10): %f" % (time.time()-a),'I')

      a=time.time()
      magnets=contract.functions.getMagnets(0,100).call()
      log("getMagnets (100): %f" % (time.time()-a),'I')
      continue

    #--- remote search command
    if cmd.startswith('/remote'):
      word=cmd.split(' ')[1]
      mcount=contract.functions.getMagnetCount().call()
      step=100
      searchResults.clear()
      fcount=0
      for i in range(0,mcount,step):
        smin=i
        smax=i+step
        if (smax>mcount): smax=mcount
        log('Searching remotely for "%s" on %d-%d from %d torrents' % (word,smin,smax,mcount),'I')
        (count,magnets)=contract.functions.searchMagnet(smin,smax,word.encode('utf-8')).call()
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
      magnet=contract.functions.getMagnet(Id).call()
      i=Magnet.unpackMagnet(magnet)
      print("\n")
      print("%s size:%d bytes seeders:%d leechers:%d votes: %d" % (i[1],i[2],i[4],i[5],i[8]))
      a=input('About to vote up that torrent, proceed (y/n)?')
      if (a.lower()=='y'):
        fcall=contract.functions.vote(Id)
        sendTransaction(fcall)
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
          packedMagnets.append(m.packMagnet())
          # publish blocks of 10 torrents
          if len(packedMagnets)==10:
              try:
                fcall=contract.functions.createMagnet10(packedMagnets)
                sendTransaction(fcall)
                print("Magnets created successfully. Id is %d" % fcall.call())
              except Exception as e:
                log(e,"E")
              print("Sent Magnets %d to %d" % (mcount-10,mcount))
              packedMagnets=[]
        except Exception as e:
            log(e,"E")
            pass
      # send remaining torrents
      from web3.gas_strategies.rpc import rpc_gas_price_strategy
      web3.eth.set_gas_price_strategy(rpc_gas_price_strategy)
      for i in packedMagnets:
        try:
          print("Sending torrent with infohash: %s" % i[0].hex())
          fcall=contract.functions.createMagnet(i)
          sendTransaction(fcall)
          print("Torrent ID is %d" % fcall.call())
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
