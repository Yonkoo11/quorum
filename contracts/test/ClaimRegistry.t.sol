// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import { Test } from "forge-std/Test.sol";
import { ClaimRegistry, IQuorumToken } from "../src/ClaimRegistry.sol";
import { MockToken, NoReturnToken } from "./MockToken.sol";

contract ClaimRegistryTest is Test {
    uint256 constant FEE = 100_000e18;
    MockToken token;
    ClaimRegistry registry;
    address alice = makeAddr("alice");
    address bob = makeAddr("bob");
    bytes32 constant DIGEST = keccak256("a finding");

    event Claimed(bytes32 indexed digest, address indexed claimant, uint256 fee);

    function setUp() public {
        token = new MockToken();
        registry = new ClaimRegistry(IQuorumToken(address(token)), FEE);
        token.mint(alice, 10 * FEE);
        token.mint(bob, 10 * FEE);
        vm.prank(alice); token.approve(address(registry), type(uint256).max);
        vm.prank(bob); token.approve(address(registry), type(uint256).max);
    }

    function test_ClaimPullsAndBurnsExactlyTheFeeAndEmits() public {
        uint256 supply = token.totalSupply();
        vm.warp(1_757_600_000);
        vm.expectEmit(true, true, false, true, address(registry));
        emit Claimed(DIGEST, alice, FEE);
        vm.prank(alice); registry.claim(DIGEST);
        assertEq(token.balanceOf(alice), 9 * FEE);
        assertEq(token.totalSupply(), supply - FEE);
        assertEq(token.balanceOf(address(registry)), 0);
        assertEq(registry.claimedAt(DIGEST, alice), 1_757_600_000);
    }

    function test_NoAllowanceRevertsAndRecordsNothing() public {
        vm.prank(alice); token.approve(address(registry), 0);
        vm.prank(alice); vm.expectRevert(ClaimRegistry.TransferFailed.selector); registry.claim(DIGEST);
        assertEq(registry.claimedAt(DIGEST, alice), 0);
        assertEq(token.balanceOf(alice), 10 * FEE);
    }

    function test_NoBalanceRevertsAndRecordsNothing() public {
        address poor = makeAddr("poor");
        vm.prank(poor); token.approve(address(registry), type(uint256).max);
        vm.prank(poor); vm.expectRevert(ClaimRegistry.TransferFailed.selector); registry.claim(DIGEST);
        assertEq(registry.claimedAt(DIGEST, poor), 0);
    }

    function test_ZeroDigestReverts() public {
        vm.prank(alice); vm.expectRevert(ClaimRegistry.ZeroDigest.selector); registry.claim(bytes32(0));
    }

    function test_RepeatRevertsAndKeepsTheFirstTime() public {
        vm.warp(100); vm.prank(alice); registry.claim(DIGEST);
        vm.warp(200); vm.prank(alice); vm.expectRevert(ClaimRegistry.AlreadyClaimed.selector); registry.claim(DIGEST);
        assertEq(registry.claimedAt(DIGEST, alice), 100);
        assertEq(token.balanceOf(alice), 9 * FEE);
    }

    function test_SameDigestTwoClaimantsBothRecordedBothPaid() public {
        uint256 supply = token.totalSupply();
        vm.prank(alice); registry.claim(DIGEST);
        vm.prank(bob); registry.claim(DIGEST);
        assertGt(registry.claimedAt(DIGEST, alice), 0);
        assertGt(registry.claimedAt(DIGEST, bob), 0);
        assertEq(token.totalSupply(), supply - 2 * FEE);
    }

    function test_AFrontRunDoesNotBlockTheRealClaim() public {
        vm.prank(bob); registry.claim(DIGEST);       // bob copied alice's digest and landed first
        vm.prank(alice); registry.claim(DIGEST);     // alice's claim still lands
        assertGt(registry.claimedAt(DIGEST, alice), 0);
    }

    function test_ReturnFalseTokenReverts() public {
        token.setReturnFalse(true);
        vm.prank(alice); vm.expectRevert(ClaimRegistry.TransferFailed.selector); registry.claim(DIGEST);
        assertEq(registry.claimedAt(DIGEST, alice), 0);
    }

    function test_NoReturnValueTokenWorks() public {
        NoReturnToken t = new NoReturnToken();
        ClaimRegistry r = new ClaimRegistry(IQuorumToken(address(t)), FEE);
        t.mint(alice, FEE);
        vm.prank(alice); t.approve(address(r), FEE);
        vm.prank(alice); r.claim(DIGEST);
        assertGt(r.claimedAt(DIGEST, alice), 0);
        assertEq(t.totalSupply(), 0);
    }

    function test_FeeOnTransferTokenRevertsNamingTheShortfall() public {
        token.setFeeBps(100); // 1% vanishes
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(ClaimRegistry.FeeNotReceived.selector, FEE - FEE / 100));
        registry.claim(DIGEST);
        assertEq(registry.claimedAt(DIGEST, alice), 0);
    }

    function test_RevertingBurnRevertsTheWholeClaim() public {
        token.setBurnReverts(true);
        vm.prank(alice); vm.expectRevert(bytes("burn refused")); registry.claim(DIGEST);
        assertEq(token.balanceOf(alice), 10 * FEE);
        assertEq(registry.claimedAt(DIGEST, alice), 0);
    }

    function test_NoopBurnReverts() public {
        token.setBurnNoop(true);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(ClaimRegistry.FeeNotBurned.selector, FEE));
        registry.claim(DIGEST);
    }

    function test_ReentryDuringTransferIsRefused() public {
        token.setReenter(registry, keccak256("another"));
        uint256 supply = token.totalSupply();
        vm.prank(alice); registry.claim(DIGEST);
        assertTrue(token.reenterReverted(), "the inner claim must revert");
        assertEq(registry.claimedAt(keccak256("another"), address(token)), 0);
        assertEq(token.totalSupply(), supply - FEE, "exactly one fee burned");
    }

    function test_DonatedTokensBurnAtTheNextClaim() public {
        token.mint(address(registry), 5e18);
        uint256 supply = token.totalSupply();
        vm.prank(alice); registry.claim(DIGEST);
        assertEq(token.balanceOf(address(registry)), 0);
        assertEq(token.totalSupply(), supply - FEE - 5e18);
    }

    function test_ConstructorRejectsZeroFeeAndNonContractToken() public {
        vm.expectRevert(bytes("fee is zero"));
        new ClaimRegistry(IQuorumToken(address(token)), 0);
        vm.expectRevert(bytes("token is not a contract"));
        new ClaimRegistry(IQuorumToken(alice), FEE);
    }

    function test_EtherIsRefused() public {
        vm.deal(alice, 1 ether);
        vm.prank(alice);
        (bool ok, ) = address(registry).call{ value: 1 }("");
        assertFalse(ok);
    }

    function test_ImmutablesReadBack() public view {
        assertEq(registry.fee(), FEE);
        assertEq(address(registry.token()), address(token));
    }

    function testFuzz_TwoClaimantsBurnTwoFeesAndARepeatBurnsNothing(bytes32 d, address a, address b) public {
        vm.assume(d != bytes32(0) && a != b && a != address(0) && b != address(0));
        vm.assume(a.code.length == 0 && b.code.length == 0 && a != address(token) && b != address(token));
        token.mint(a, FEE); token.mint(b, FEE);
        vm.prank(a); token.approve(address(registry), FEE);
        vm.prank(b); token.approve(address(registry), FEE);
        uint256 supply = token.totalSupply();
        vm.prank(a); registry.claim(d);
        vm.prank(b); registry.claim(d);
        assertEq(token.totalSupply(), supply - 2 * FEE);
        vm.prank(a); vm.expectRevert(ClaimRegistry.AlreadyClaimed.selector); registry.claim(d);
        assertEq(token.totalSupply(), supply - 2 * FEE);
    }
}

/// Random claims from funded actors; the registry must burn exactly one fee per distinct (digest, claimant).
contract Handler is Test {
    ClaimRegistry public registry;
    MockToken public token;
    address[] public actors;
    bytes32[] public digests;
    uint256 public successes;
    mapping(bytes32 => mapping(address => bool)) seen;
    uint256 public distinctPairs;

    constructor(ClaimRegistry r, MockToken t) {
        registry = r; token = t;
        for (uint256 i = 0; i < 4; i++) {
            address a = makeAddr(string(abi.encodePacked("actor", i)));
            actors.push(a);
            token.mint(a, 1_000 * registry.fee());
            vm.prank(a); token.approve(address(r), type(uint256).max);
        }
        digests.push(bytes32(0));
        for (uint256 i = 1; i < 6; i++) digests.push(keccak256(abi.encodePacked("digest", i)));
    }

    function claim(uint256 actorSeed, uint256 digestSeed) external {
        address a = actors[actorSeed % actors.length];
        bytes32 d = digests[digestSeed % digests.length];
        vm.prank(a);
        try registry.claim(d) {
            successes++;
            if (!seen[d][a]) { seen[d][a] = true; distinctPairs++; }
        } catch {}
    }
}

contract ClaimRegistryInvariant is Test {
    uint256 constant FEE = 100_000e18;
    MockToken token;
    ClaimRegistry registry;
    Handler handler;
    uint256 initialSupply;

    function setUp() public {
        token = new MockToken();
        registry = new ClaimRegistry(IQuorumToken(address(token)), FEE);
        handler = new Handler(registry, token);
        initialSupply = token.totalSupply();
        targetContract(address(handler));
    }

    function invariant_OneFeePerDistinctClaim() public view {
        assertEq(token.totalSupply(), initialSupply - FEE * handler.successes());
        assertEq(handler.successes(), handler.distinctPairs());
        assertEq(token.balanceOf(address(registry)), 0);
    }
}
