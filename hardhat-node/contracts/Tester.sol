//SPDX-License-Identifier: AGPL
pragma solidity ^0.8.0;

import "hardhat/console.sol";

contract Tester {
    string private greeting;
    uint private value;

    constructor(string memory _greeting) {
        console.log("Deploying a Greeter with greeting:", _greeting);
        greeting = _greeting;
    }

    function greet() public view returns (string memory) {
        return greeting;
    }

    function setOnlyEven(uint newValue) public {
        require(newValue % 2 == 0, 'Not an even number');
        console.log("Changing value from '%d' to '%d'", value, newValue);
        value = newValue;
    }

    function setGreeting(string memory _greeting) public {
        console.log("Changing greeting from '%s' to '%s'", greeting, _greeting);
        greeting = _greeting;
    }
}
