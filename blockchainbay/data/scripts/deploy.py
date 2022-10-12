from brownie import BlockchainBay,accounts,network

def main():
    account = accounts.load('polygon-account','')
    t = BlockchainBay.deploy({'from':account})
    print("Deployed: "+repr(t))
