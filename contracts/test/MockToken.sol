// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import { ClaimRegistry } from "../src/ClaimRegistry.sol";

/// A token whose misbehaviour can be switched on one flag at a time.
contract MockToken {
    string public constant name = "Mock";
    uint8 public constant decimals = 18;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    bool public returnFalse;      // transferFrom returns false and moves nothing
    uint256 public feeBps;        // fee-on-transfer: this much of every transfer vanishes
    bool public burnReverts;
    bool public burnNoop;         // burn returns without burning
    ClaimRegistry public reenterInto;   // during transferFrom, call claim(reenterDigest) on this registry
    bytes32 public reenterDigest;
    bool public reenterReverted;

    function mint(address to, uint256 amount) external { balanceOf[to] += amount; totalSupply += amount; }
    function setReturnFalse(bool v) external { returnFalse = v; }
    function setFeeBps(uint256 v) external { feeBps = v; }
    function setBurnReverts(bool v) external { burnReverts = v; }
    function setBurnNoop(bool v) external { burnNoop = v; }
    function setReenter(ClaimRegistry r, bytes32 d) external { reenterInto = r; reenterDigest = d; }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        if (returnFalse) return false;
        uint256 allowed = allowance[from][msg.sender];
        require(allowed >= amount, "allowance");
        require(balanceOf[from] >= amount, "balance");
        allowance[from][msg.sender] = allowed - amount;
        uint256 lost = amount * feeBps / 10_000;
        balanceOf[from] -= amount;
        balanceOf[to] += amount - lost;
        totalSupply -= lost;
        if (address(reenterInto) != address(0)) {
            try reenterInto.claim(reenterDigest) { reenterReverted = false; } catch { reenterReverted = true; }
        }
        return true;
    }

    function burn(uint256 amount) external {
        require(!burnReverts, "burn refused");
        if (burnNoop) return;
        require(balanceOf[msg.sender] >= amount, "balance");
        balanceOf[msg.sender] -= amount;
        totalSupply -= amount;
    }
}

/// A token whose transferFrom returns nothing at all (the USDT shape).
contract NoReturnToken {
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 amount) external { balanceOf[to] += amount; totalSupply += amount; }
    function approve(address spender, uint256 amount) external { allowance[msg.sender][spender] = amount; }
    function transferFrom(address from, address to, uint256 amount) external {
        require(allowance[from][msg.sender] >= amount && balanceOf[from] >= amount, "no");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
    }
    function burn(uint256 amount) external {
        balanceOf[msg.sender] -= amount;
        totalSupply -= amount;
    }
}
