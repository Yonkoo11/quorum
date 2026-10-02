// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

/// QUORUM, the claim fee token.
///
/// The fee for a claim is paid in QUORUM and burned by ClaimRegistry in the same transaction, so a
/// record cannot exist without its own cost. This is the Arbitrum One deployment of that same fee
/// token; the live market is on Robinhood Chain. A plain ERC-20 with a holder-only burn, no owner,
/// no mint after construction, no pause, no upgrade.
contract QuorumToken {
    string public constant name = "Quorum";
    string public constant symbol = "QUORUM";
    uint8 public constant decimals = 18;

    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    /// Mint the whole supply once, to `to`. There is no other path that creates tokens.
    constructor(uint256 initialSupply, address to) {
        require(to != address(0), "to zero");
        totalSupply = initialSupply;
        balanceOf[to] = initialSupply;
        emit Transfer(address(0), to, initialSupply);
    }

    function transfer(address to, uint256 value) external returns (bool) {
        _transfer(msg.sender, to, value);
        return true;
    }

    function approve(address spender, uint256 value) external returns (bool) {
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) external returns (bool) {
        uint256 allowed = allowance[from][msg.sender];
        if (allowed != type(uint256).max) {
            require(allowed >= value, "allowance");
            allowance[from][msg.sender] = allowed - value;
            emit Approval(from, msg.sender, allowed - value);
        }
        _transfer(from, to, value);
        return true;
    }

    /// Burn `value` from the caller. ClaimRegistry calls this on the fee it just received.
    function burn(uint256 value) external {
        uint256 bal = balanceOf[msg.sender];
        require(bal >= value, "balance");
        unchecked {
            balanceOf[msg.sender] = bal - value;
            totalSupply -= value;
        }
        emit Transfer(msg.sender, address(0), value);
    }

    function _transfer(address from, address to, uint256 value) internal {
        require(to != address(0), "to zero");
        uint256 bal = balanceOf[from];
        require(bal >= value, "balance");
        unchecked {
            balanceOf[from] = bal - value;
            balanceOf[to] += value;
        }
        emit Transfer(from, to, value);
    }
}
