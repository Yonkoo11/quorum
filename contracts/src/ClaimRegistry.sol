// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

/// The QUORUM token, the two functions the registry needs.
interface IQuorumToken {
    function balanceOf(address account) external view returns (uint256);
    function burn(uint256 amount) external;
}

/// One fee, one claim.
///
/// A claim is "this address knew this digest at this time". The registry records it and takes the fee in
/// the same transaction: the fee is pulled from the claimant and burned through the token's own burn, and
/// the record is only written if both happened. So a record cannot exist without its own fee, and a fee
/// cannot back two records. No owner, no pause, no upgrade, no ether, nothing to sweep: whatever the
/// registry holds is burned at the next claim. A different fee is a different registry.
contract ClaimRegistry {
    IQuorumToken public immutable token;
    uint256 public immutable fee;

    /// Block time at which `claimant` recorded `digest`; 0 means never.
    mapping(bytes32 digest => mapping(address claimant => uint256 at)) public claimedAt;

    uint256 private _entered = 1;

    event Claimed(bytes32 indexed digest, address indexed claimant, uint256 fee);

    error ZeroDigest();
    error AlreadyClaimed();
    error TransferFailed();
    error FeeNotReceived(uint256 received);
    error FeeNotBurned(uint256 left);
    error Reentered();

    constructor(IQuorumToken token_, uint256 fee_) {
        require(address(token_).code.length != 0, "token is not a contract");
        require(fee_ != 0, "fee is zero");
        token = token_;
        fee = fee_;
    }

    /// Record `digest` for the caller and burn the fee. Reverts unless at least `fee` arrived and every
    /// token the registry held was burned. The same (digest, claimant) can be recorded once.
    function claim(bytes32 digest) external {
        if (_entered != 1) revert Reentered();
        _entered = 2;
        if (digest == bytes32(0)) revert ZeroDigest();
        if (claimedAt[digest][msg.sender] != 0) revert AlreadyClaimed();
        claimedAt[digest][msg.sender] = block.timestamp;

        uint256 before = token.balanceOf(address(this));
        // transferFrom(msg.sender, this, fee); a token that returns nothing is accepted, one that returns false is not
        (bool ok, bytes memory ret) =
            address(token).call(abi.encodeWithSelector(0x23b872dd, msg.sender, address(this), fee));
        if (!ok || (ret.length != 0 && !abi.decode(ret, (bool)))) revert TransferFailed();
        uint256 held = token.balanceOf(address(this));
        if (held < before + fee) revert FeeNotReceived(held > before ? held - before : 0);

        token.burn(held);
        uint256 left = token.balanceOf(address(this));
        if (left != 0) revert FeeNotBurned(left);

        emit Claimed(digest, msg.sender, fee);
        _entered = 1;
    }
}
