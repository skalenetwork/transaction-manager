// SPDX-License-Identifier: AGPL-3.0-only
pragma solidity 0.8.38;

contract Tester {
    uint256 private value;

    function setOnlyEven(uint256 newValue) external {
        require(newValue % 2 == 0, "Not an even number");
        value = newValue;
    }
}
