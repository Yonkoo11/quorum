// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Teaching fixture. Known-vulnerable on purpose: the external call
/// happens before the balance is written, and there is no reentrancy guard.
/// Quorum learns the shape here, then recognises it in production source.
contract VulnerableVault {
    mapping(address => uint256) public balances;
    address public owner;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "send failed");
        balances[msg.sender] = balances[msg.sender] - amount;
    }
}
