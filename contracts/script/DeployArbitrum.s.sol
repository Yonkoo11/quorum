// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import { Script, console2 } from "forge-std/Script.sol";
import { ClaimRegistry, IQuorumToken } from "../src/ClaimRegistry.sol";
import { QuorumToken } from "../src/QuorumToken.sol";

/// Arbitrum One deployment of Quorum's claim layer: the QUORUM fee token, the ClaimRegistry, and one
/// real claim recorded on-chain so the mechanism is live end-to-end (not a dead deploy).
///
/// forge script script/DeployArbitrum.s.sol:DeployArbitrum --rpc-url https://arb1.arbitrum.io/rpc --broadcast --slow
/// The key is read from DEPLOYER_PRIVATE_KEY in the environment and never printed.
contract DeployArbitrum is Script {
    uint256 constant FEE = 100_000e18;        // same fee as Robinhood Chain
    uint256 constant SUPPLY = 1_000_000e18;   // enough for the first claims; no mint after this

    function run() external {
        require(block.chainid == 42161, "Arbitrum One only (chainid 42161)");
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address me = vm.addr(pk);

        vm.startBroadcast(pk);
        QuorumToken token = new QuorumToken(SUPPLY, me);
        ClaimRegistry registry = new ClaimRegistry(IQuorumToken(address(token)), FEE);
        token.approve(address(registry), FEE);
        // Record one real claim: the digest of a proven finding, settled on Arbitrum One.
        bytes32 digest = keccak256("quorum: proof settled on Arbitrum One, Open House Singapore");
        registry.claim(digest);
        vm.stopBroadcast();

        console2.log("QuorumToken   ", address(token));
        console2.log("ClaimRegistry ", address(registry));
        console2.log("claimant      ", me);
        console2.log("block         ", block.number);
    }
}
