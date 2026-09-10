// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Teaching fixture. Known-vulnerable on purpose: a privileged value is
/// writable by anyone, with no modifier and no msg.sender check on the path.
contract OpenFeeSetter {
    uint256 public feeRate;
    address public treasury;
    uint256 public lastUpdate;

    function setFeeRate(uint256 newRate) external {
        feeRate = newRate;
        lastUpdate = block.timestamp;
    }

    function setTreasury(address newTreasury) external {
        treasury = newTreasury;
    }
}
