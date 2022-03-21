FROM node:14

ENV NODE_OPTIONS="--max-old-space-size=2048"

RUN mkdir /app

WORKDIR /app 

RUN apt-get update && apt-get install build-essential

COPY package.json hardhat.config.ts yarn.lock ./

RUN yarn install

CMD npx hardhat node
