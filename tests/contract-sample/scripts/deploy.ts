import { ethers } from "hardhat";
import { promises as fs } from "fs";

async function main() {
  const Tester = await ethers.getContractFactory("Tester");
  const tester = await Tester.deploy("Tester, test!");

  await tester.deployed();

  console.log("Tester deployed to:", tester.address);


  let abi = JSON.parse(await fs.readFile("artifacts/contracts/Tester.sol/Tester.json", "utf-8"));
  abi.address = tester.address
  await fs.writeFile("abi.json", JSON.stringify(abi, null, 4));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
