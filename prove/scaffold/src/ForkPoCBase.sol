// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

interface IERC20Bal {
    function balanceOf(address) external view returns (uint256);
}

/// @title ForkPoCBase — the scaffold every Quorum proof inherits.
/// @notice A proof is not what the exploit asserts. It is what this base measures: the attacker's
///         holding of one declared asset is snapshotted before the attack and after, and the
///         `[PROOF]` line is emitted only when it grew. A model that writes `assertTrue(true)` proves
///         nothing here, because it never touches this measurement.
///
///         Ported from bughunter/tools/fork-poc (MIT, this repo's owner), widened to any chain: the
///         fork endpoint is chosen by name through foundry.toml `[rpc_endpoints]`, so no key is in code.
abstract contract ForkPoCBase is Test {
    address internal attacker;

    /// @param chain  a name in foundry.toml `[rpc_endpoints]` (ethereum, base, bsc, polygon, ...).
    /// @param block_ the block to fork; use the exploit's parent block so the bug is still live.
    function forkAt(string memory chain, uint256 block_) internal {
        vm.createSelectFork(vm.rpcUrl(chain), block_);
        attacker = makeAddr("quorum-attacker");
        vm.deal(attacker, 1 ether); // gas only, never counted as profit
    }

    /// @notice Native-token profit: snapshot around the attack, emit `[PROOF]` only if it rose.
    function proveEthProfit(function() external attack) internal {
        uint256 before = attacker.balance;
        attack();
        _report("ETH", attacker.balance, before);
    }

    /// @notice ERC-20 profit in `token`: snapshot around the attack, emit `[PROOF]` only if it rose.
    function proveTokenProfit(address token, function() external attack) internal {
        uint256 before = IERC20Bal(token).balanceOf(attacker);
        attack();
        _report(vm.toString(token), IERC20Bal(token).balanceOf(attacker), before);
    }

    function _report(string memory asset, uint256 nowBal, uint256 before) private {
        console.log("[before] attacker", asset, before);
        console.log("[after ] attacker", asset, nowBal);
        require(nowBal > before, "NO PROFIT: attacker balance did not grow, the exploit did not pay");
        console.log("[PROOF] attacker gained", asset, nowBal - before);
    }
}
