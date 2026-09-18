// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import { Test } from "forge-std/Test.sol";
import { ClaimRegistry, IQuorumToken } from "../src/ClaimRegistry.sol";

interface IERC20Like {
    function approve(address, uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
    function totalSupply() external view returns (uint256);
}

/// Against the real token on Robinhood Chain. Runs only when QUORUM_RPC is set:
///   forge test --match-contract Fork --fork-url "$QUORUM_RPC" --evm-version cancun -vvv
/// (cancun: the token's own bytecode uses PUSH0, so the fork EVM must be at least Shanghai)
contract ClaimRegistryFork is Test {
    address constant TOKEN = 0xa6452Fd7134218f62056a304eaf501F8714A26b9;
    uint256 constant FEE = 100_000e18;
    address constant HOLDER = 0x29645627E382a1EEa17593A0cFAeA2867F6C0ceB;

    function test_RealTokenPullsAndBurnsExactlyTheFee() public {
        if (block.chainid != 4663) { vm.skip(true); return; }
        ClaimRegistry r = new ClaimRegistry(IQuorumToken(TOKEN), FEE);
        // a real holder, impersonated on the fork; nothing is sent anywhere
        address actor = HOLDER;
        uint256 held = IERC20Like(TOKEN).balanceOf(actor);
        if (held < FEE) { vm.skip(true); return; }
        uint256 supply = IERC20Like(TOKEN).totalSupply();
        vm.prank(actor); IERC20Like(TOKEN).approve(address(r), FEE);
        vm.recordLogs();
        vm.prank(actor); r.claim(keccak256("fork"));
        assertEq(IERC20Like(TOKEN).balanceOf(actor), held - FEE);
        assertEq(IERC20Like(TOKEN).balanceOf(address(r)), 0);
        assertEq(IERC20Like(TOKEN).totalSupply(), supply - FEE, "the real burn reduces supply by exactly the fee");
        assertGt(r.claimedAt(keccak256("fork"), actor), 0);
    }
}
