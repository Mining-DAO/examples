// Deployed at https://etherscan.io/address/0x8512a66d249e3b51000b772047c8545ad010f27c#code

pragma solidity 0.6.12;

contract TransferValueToMinerCoinbase {

    receive() external payable {
        block.coinbase.transfer(msg.value);
    }

}
