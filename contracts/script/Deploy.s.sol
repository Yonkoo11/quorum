// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import { Script, console2 } from "forge-std/Script.sol";
import { ClaimRegistry, IQuorumToken } from "../src/ClaimRegistry.sol";

/// forge script script/Deploy.s.sol:Deploy --rpc-url "$QUORUM_RPC" --broadcast --slow
/// The key is read from DEPLOYER_PRIVATE_KEY in the environment and never printed.
contract Deploy is Script {
    address constant TOKEN = 0xa6452Fd7134218f62056a304eaf501F8714A26b9;
    uint256 constant FEE = 100_000e18;

    function run() external {
        require(block.chainid == 4663, "the registry is deployed on Robinhood Chain only");
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(pk);
        ClaimRegistry registry = new ClaimRegistry(IQuorumToken(TOKEN), FEE);
        vm.stopBroadcast();
        console2.log("ClaimRegistry", address(registry));
        console2.log("block", block.number);
    }
}
