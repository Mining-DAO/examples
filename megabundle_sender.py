# Minimal example of sending a Megabundle to Flashbots

import json
import os
import requests
import rlp
from rlp.sedes import CountableList, binary, big_endian_int
import time

import eth_account
import web3

# MiningDAO public example endpoint, please don't abuse
INFURA_ENDPOINT = 'https://mainnet.infura.io/v3/dce4f913d749454d94daa2c87f01ceb2'
w3 = web3.Web3(web3.HTTPProvider(INFURA_ENDPOINT))

MEGABUNGLE_RPC = 'http://127.0.0.1:8545'

INCLUSION_FEE = int(0.1337e18)

# This address is used both to create a fee-paying transaction and for trusted relay signature
ACCOUNT_ADDRESS = os.getenv('BUNDLE_ACCOUNT')
ACCOUNT_PRIVKEY = os.getenv('BUNDLE_PRIVKEY')


def send_request(endpoint, payload, headers):
    response = requests.post(
        endpoint,
        data=json.dumps(payload),
        headers=headers,
        timeout=10.0,
    ).json()
    print(response)
    if response is not None and isinstance(response, dict) and 'result' in response:
        return response['result']
    else:
        print(f'Looks like we got an error! Message {response}')
        return None


def sign_bribe_tx():
    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
    TRANSFER_GAS = 21000
    bribe_tx = w3.eth.account.sign_transaction(
        dict(nonce=nonce, gasPrice=INCLUSION_FEE // TRANSFER_GAS, gas=TRANSFER_GAS, to=ACCOUNT_ADDRESS,
             value=INCLUSION_FEE, data=b''),
        ACCOUNT_PRIVKEY)
    return bribe_tx.rawTransaction.hex()


class UnsignedMegabundle(rlp.Serializable):
    fields = [
        ('txs', CountableList(binary)),
        ('blockNumber', big_endian_int),
        ('minTimestamp', big_endian_int),
        ('maxTimestamp', big_endian_int),
        ('revertingTxHashes', CountableList(binary)),
    ]


def send_megabundle(megabundle):
    unsigned_megabundle = UnsignedMegabundle(
        txs=[bytes.fromhex(tx[2:]) for tx in megabundle['txs']],
        blockNumber=megabundle['blockNumber'],
        minTimestamp=megabundle['minTimestamp'] if 'minTimestamp' in megabundle else 0,
        maxTimestamp=megabundle['maxTimestamp'] if 'maxTimestamp' in megabundle else 0,
        revertingTxHashes=megabundle['revertingTxHashes'] if 'revertingTxHashes' in megabundle else [])
    rlp_encoding = rlp.encode(unsigned_megabundle)
    print('rlp_encoding', rlp_encoding.hex())
    megabundle['relaySignature'] = web3.Account.sign_message(
        eth_account.messages.encode_defunct(primitive=rlp_encoding),
        private_key=ACCOUNT_PRIVKEY
    ).signature.hex()
    print('relay signature', megabundle['relaySignature'])
    headers = {'Content-Type': 'application/json'}
    payload = {'jsonrpc': '2.0', 'method': 'eth_sendMegabundle', 'params': [megabundle]}
    return send_request(MEGABUNGLE_RPC, payload, headers)


if __name__ == '__main__':
    balance = w3.eth.getBalance(ACCOUNT_ADDRESS)
    assert balance > 1.1 * INCLUSION_FEE, 'Not enough money on account, cannot pay for bundles'

    tx = sign_bribe_tx()
    print('Sending this TX as a Megabundle', tx)
    megabundle = {'txs': [tx], 'blockNumber': w3.eth.blockNumber + 2}
    send_megabundle(megabundle)
