import os
import time
from dotenv import load_dotenv
from web3 import Web3
from web3.constants import MAX_INT
from web3.middleware import ExtraDataToPOAMiddleware
from requests.exceptions import HTTPError

def with_retry(func, max_retries=5, initial_delay=1):
    """Retry function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except HTTPError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)  # exponential backoff
                print(f"Rate limited. Retrying in {delay} seconds...")
                time.sleep(delay)
                continue
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                print(f"Error: {str(e)}. Retrying in {delay} seconds...")
                time.sleep(delay)
                continue
            raise

def get_web3_provider():
    """Get Web3 provider with fallback RPC URLs"""
    rpc_urls = [
        'https://polygon.llamarpc.com',
        'https://polygon-rpc.com',
        'https://rpc-mainnet.matic.network',
        # Add more fallback RPC URLs as needed
    ]
    
    for rpc_url in rpc_urls:
        try:
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            # Test the connection
            web3.eth.block_number
            print(f"Connected to {rpc_url}")
            return web3
        except Exception as e:
            print(f"Failed to connect to {rpc_url}: {str(e)}")
            continue
    
    raise Exception("Failed to connect to any RPC endpoint")

def set_allowances():
    load_dotenv()

    priv_key = os.getenv('PK')
    pub_key = os.getenv('PBK')
    chain_id = 137

    erc20_approve = '''[{"constant": false,"inputs": [{"name": "_spender","type": "address" },{ "name": "_value", "type": "uint256" }],"name": "approve","outputs": [{ "name": "", "type": "bool" }],"payable": false,"stateMutability": "nonpayable","type": "function"}]'''
    erc1155_set_approval = '''[{"inputs": [{ "internalType": "address", "name": "operator", "type": "address" },{ "internalType": "bool", "name": "approved", "type": "bool" }],"name": "setApprovalForAll","outputs": [],"stateMutability": "nonpayable","type": "function"}]'''

    usdc_address = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
    ctf_address = '0x4D97DCd97eC945f40cF65F87097ACe5EA0476045'

    web3 = get_web3_provider()
    
    def check_balance():
        balance = web3.eth.get_balance(pub_key)
        if balance == 0:
            raise Exception('No MATIC in your wallet')
        print(f'Current MATIC balance: {web3.from_wei(balance, "ether")} MATIC')
        return balance

    def send_approval_transaction(contract, func, spender, value=None):
        nonce = web3.eth.get_transaction_count(pub_key)
        
        if value is not None:
            raw_txn = func(spender, value).build_transaction({
                'chainId': chain_id,
                'from': pub_key,
                'nonce': nonce
            })
        else:
            raw_txn = func(spender, True).build_transaction({
                'chainId': chain_id,
                'from': pub_key,
                'nonce': nonce
            })

        signed_tx = web3.eth.account.sign_transaction(raw_txn, private_key=priv_key)
        tx_hash = with_retry(lambda: web3.eth.send_raw_transaction(signed_tx.raw_transaction))
        tx_receipt = with_retry(lambda: web3.eth.wait_for_transaction_receipt(tx_hash, timeout=600))
        return tx_receipt

    # Check balance
    with_retry(check_balance)

    # Set up contracts
    usdc = web3.eth.contract(address=usdc_address, abi=erc20_approve)
    ctf = web3.eth.contract(address=ctf_address, abi=erc1155_set_approval)

    # Addresses to approve
    addresses_to_approve = [
        '0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E',  # CTF Exchange
        '0xC5d563A36AE78145C45a50134d48A1215220f80a',  # Neg Risk CTF Exchange
        '0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296'   # Neg Risk Adapter
    ]

    # Process approvals
    for address in addresses_to_approve:
        print(f"\nProcessing approvals for {address}")
        
        # USDC approval
        print("Sending USDC approval...")
        receipt = send_approval_transaction(
            usdc,
            usdc.functions.approve,
            address,
            int(MAX_INT, 0)
        )
        print(f"USDC approval complete. Transaction hash: {receipt['transactionHash'].hex()}")

        # CTF approval
        print("Sending CTF approval...")
        receipt = send_approval_transaction(
            ctf,
            ctf.functions.setApprovalForAll,
            address
        )
        print(f"CTF approval complete. Transaction hash: {receipt['transactionHash'].hex()}")

if __name__ == "__main__":
    set_allowances()