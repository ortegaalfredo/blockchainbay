from brownie import BlockchainBay,accounts

def main():
    account = accounts.load('ganache_account','ganache')
    t = BlockchainBay.deploy({'from':account})
    print("Deployed: "+repr(t))
