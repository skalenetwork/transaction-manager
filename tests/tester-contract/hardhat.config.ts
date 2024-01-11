import * as dotenv from "dotenv";

import { HardhatUserConfig, task } from "hardhat/config";
import "@nomiclabs/hardhat-etherscan";
import "@nomiclabs/hardhat-waffle";
import "@typechain/hardhat";
import "hardhat-gas-reporter";
import "solidity-coverage";
import { utils, Wallet } from "ethers";

dotenv.config();


function getCustomPrivateKey(privateKey: string | undefined) {
  if (privateKey) {
    return [privateKey];
  } else {
    return [];
  }
}

function getAccounts() {
    var accounts = [];
    if (process.env.PRIVATE_KEY) {
        var plainKey = new Wallet(process.env.PRIVATE_KEY).privateKey;
        var balance = utils.parseEther("2000000").toString();
        accounts.push({
            privateKey: plainKey,
            balance: balance
        });
    }   
    return accounts;
}

task("accounts", "Prints the list of accounts", async (taskArgs, hre) => {
  const accounts = await hre.ethers.getSigners();

  for (const account of accounts) {
    console.log(account.address);
  }
});

const config: HardhatUserConfig = {
  solidity: "0.8.4",
  networks: {
    ropsten: {
      url: process.env.ROPSTEN_URL || "",
      accounts:
        process.env.PRIVATE_KEY !== undefined ? [process.env.PRIVATE_KEY] : [],
    },
    hardhat: {
      accounts: getAccounts(),
      chainId: 31337,
      blockGasLimit: 12000000,
      gasPrice: 1000000000,
      mining: {
          auto: true,
          interval: 1000
      }
    }
  },
  gasReporter: {
    enabled: process.env.REPORT_GAS !== undefined,
    currency: "USD",
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY,
  },
};

export default config;
