# Minimal example of sending bundles to Flashbots and MiningDAO
# 1) Constructs a sample bundle of 3 transactions
# 2) Submits that bundle, every block, until inclusion happens
# Bundle composition: TX1 self-transfer, TX2 inclusion "bribe", TX3 self-transfer
# First submits the bundle to Flashbots until inclusion, then to MiningDAO

import json
import requests
import time

import eth_account
import web3

# MiningDAO public example endpoint, please don't abuse
INFURA_ENDPOINT = 'https://mainnet.infura.io/v3/dce4f913d749454d94daa2c87f01ceb2'
w3 = web3.Web3(web3.HTTPProvider(INFURA_ENDPOINT))

FLASHBOTS_RPC = 'https://relay.flashbots.net'
MININGDAO_BUNDLE_RPC = 'https://bundle.miningdao.io'

# Any ETH sent to this address is converted into a `block.coinbase` payment (aka bribe)
BRIBE_CONTRACT_ADDRESS = '0x8512a66D249E3B51000b772047C8545Ad010f27c'

INCLUSION_FEE = int(0.01e18)

ACCOUNT_ADDRESS = 'INPUT YOURS'
ACCOUNT_PRIVKEY = 'INPUT YOURS'


def send_request(endpoint, payload, headers):
    response = requests.post(
        endpoint,
        data=json.dumps(payload),
        headers=headers,
        timeout=10.0,
    ).json()
    if response is not None and isinstance(response, dict) and 'result' in response:
        return response['result']
    else:
        print(f'Looks like we got an error! Payload {payload} response {response}')
        return None


def send_bundle_to_flashbots(bundle, target_block):
    payload = {
        'jsonrpc': '2.0',
        'method': 'eth_sendBundle',
        'params': [{'txs': bundle, 'blockNumber': hex(target_block)}],
    }
    bundle_signature = web3.Account.sign_message(
        eth_account.messages.encode_defunct(text=web3.Web3.keccak(text=json.dumps(payload)).hex()),
        private_key=ACCOUNT_PRIVKEY
    ).signature.hex()
    headers = {
        'Content-Type': 'application/json',
        'X-Flashbots-Signature': '{}:{}'.format(ACCOUNT_ADDRESS, bundle_signature),
    }
    return send_request(FLASHBOTS_RPC, payload, headers)


def send_bundle_to_miningdao(bundle, target_block):
    payload = {
        'jsonrpc': '2.0',
        'method': 'eth_sendBundle',
        'params': [{'txs': bundle, 'blockNumber': hex(target_block)}],
    }
    headers = {'Content-Type': 'application/json'}
    return send_request(MININGDAO_BUNDLE_RPC, payload, headers)


def create_example_bundle():
    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
    tx1 = w3.eth.account.sign_transaction(
        dict(nonce=nonce, gasPrice=111, gas=21000, to=ACCOUNT_ADDRESS, value=1, data=b''),
        ACCOUNT_PRIVKEY)
    tx2 = w3.eth.account.sign_transaction(
        dict(nonce=nonce + 1, gasPrice=222, gas=80000, to=BRIBE_CONTRACT_ADDRESS, value=INCLUSION_FEE, data=b''),
        ACCOUNT_PRIVKEY)
    tx3 = w3.eth.account.sign_transaction(
        dict(nonce=nonce + 2, gasPrice=333, gas=21000, to=ACCOUNT_ADDRESS, value=3, data=b''),
        ACCOUNT_PRIVKEY)
    return [tx1.rawTransaction.hex(), tx2.rawTransaction.hex(), tx3.rawTransaction.hex()]


if __name__ == '__main__':
    balance = w3.eth.getBalance(ACCOUNT_ADDRESS)
    assert balance > 2 * INCLUSION_FEE, 'Not enough money on account, cannot pay for bundles'

    bundle = create_example_bundle()
    print('Trying to get this bundle into Flashbots:', bundle)
    starting_nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
    while w3.eth.get_transaction_count(ACCOUNT_ADDRESS) == starting_nonce:
        send_bundle_to_flashbots(bundle, w3.eth.get_block_number() + 1)
        time.sleep(3.1337)
    print('Flashbots bundle successfully mined!')

    bundle = create_example_bundle()
    print('Trying to get this bundle into MiningDAO:', bundle)
    starting_nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
    while w3.eth.get_transaction_count(ACCOUNT_ADDRESS) == starting_nonce:
        send_bundle_to_miningdao(bundle, w3.eth.get_block_number() + 1)
        time.sleep(3.1337)
    print('MiningDAO bundle successfully mined!')
