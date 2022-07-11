# Blockchain Bay: 

Blockchainbay is a torrent distribution tool hosted on a EVM-compatible blockchain.
This is a tool similar to Pirate Bay, but using a EVM-compatible blockchain (Ethereum, polygon, BSC, etc.) as a database.

Doesn't require any funds to search and download torrents, only to upload a new torrent (As write operations modify the database).

![screenshot.png](https://github.com/ortegaalfredo/blockchainbay/blob/main/screenshot.png?raw=true)


## Requeriments:

You need to install the brownie python framework:

```
pipx install eth-brownie
```

Check additional instructions at https://eth-brownie.readthedocs.io/en/stable/install.html

## Searching torrents

You do not need any funds to search for torrents, only for uploading new entries.

Run the main command:


```
./blockChainBay.py
```
At start, the utility will sync with the database on the blockchain, downloading all torrents locally (this can take some minute). It's much faster to search in a local database, however you can also search for torrents remotely.

Issuing /help will show you the available commands:

## Commands

```
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
```

To search for a torrent, just enter a substring:

```
Enter search term: book
[1]: The Samurai Sword A Handbook size:9711356 bytes seeders:1 leechers:0
```

To display the magent link, use the /link <index> command:

```
Enter search term: /link 1


The Samurai Sword A Handbook size:9711356 bytes seeders:1 leechers:0


magnet:?xt=urn:btih:000329661633b3a4f5cb82dc6aed6aca350b9602&dn=The%20Samurai%20Sword%20A%20Handbook&tr=udp://tracker.coppersurfer.tk:6969/announce&tr=udp://tracker.open-internet.nl:6969/announce&tr=udp://tracker.leechers-paradise.org:6969/announce&tr=udp://tracker.internetwarriors.net:1337/announce&tr=udp://tracker.opentrackr.org:1337/announce&tr=udp://9.rarbg.to:2710/announce&tr=udp://9.rarbg.me:2710/announce&tr=http://tracker3.itzmx.com:6961/announce&tr=http://tracker1.itzmx.com:8080/announce&tr=udp://exodus.desync.com:6969/announce&tr=udp://explodie.org:6969/announce&tr=udp://ipv4.tracker.harry.lu:80/announce&tr=udp://denis.stalker.upeer.me:6969/announce&tr=udp://tracker.torrent.eu.org:451/announce&tr=udp://tracker.tiny-vps.com:6969/announce&tr=udp://thetracker.org:80/announce&tr=udp://open.demonii.si:1337/announce&tr=udp://tracker4.itzmx.com:2710/announce&tr=udp://tracker.cyberia.is:6969/announce&tr=udp://retracker.netbynet.ru:2710/announce


```

If you have the transmission-cli  bittorrent client installed, you can directly download the torrent using:

```
/download 1
```

## Configuring a custom blockchain on brownie

TODO

## Custom smart-contract

You can compile and deploy your own smart-contract database, for this, issue this command from the root dir:

To compile the smart contract:

```
brownie compile
```

And to deploy the smart contract, modify your account info editiny deploy.py and run it:

```
brownie run scripts/deploy.py
```

Deploying a smart contract will require funds in your account. The price will depend on the blockchain that you configured.

