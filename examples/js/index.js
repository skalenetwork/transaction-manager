"use strict";

const REDIS_URI = process.env.REDIS_URI;
const ENDPOINT = process.env.ENDPOINT;
const TX_RECORD_EXPIRATION = 24 * 60 * 60; // 1 day
const Redis = require("ioredis");
const redis = new Redis(REDIS_URI);
var Web3 = require("web3");
var web3 = new Web3(ENDPOINT); // your eth network endpoint

const pool = "transactions";

const genRanHex = size => [...Array(size)].map(() => Math.floor(Math.random() * 16).toString(16)).join("");

function makeId() {
    const prefix = "tx-";
    const unique = genRanHex(16);
    return prefix + unique;
}

function makeRecord(tx = {}, score) {
    const status = "PROPOSED";
    return JSON.stringify({
        "score": score,
        "status": status,
        ...tx
    });
}

function makeScore(priority) {
    const ts = parseInt(Date.now() / 1000);
    return priority * Math.pow(10, ts.toString().length) + ts;
}

async function send(tx, priority = 5) {
    console.log("Sending tx", tx);
    var id = makeId();
    var score = makeScore(priority);
    var record = makeRecord(tx, score);
    console.log(`Sending score: ${score}, record: ${record}`);
    await redis.multi()
        .set(id, record, "EX", TX_RECORD_EXPIRATION)
        .zadd(pool, score, id)
        .exec();
    return id;
}

function isFinished(record) {
    if (record == null) {
        return null;
    }
    const status = "status" in record ? record["status"] : null;
    return ["SUCCESS", "FAILED", "DROPPED"].includes(status);
}

async function getRecord(tx_id) {
    const r = await redis.get(tx_id);
    if (r != null) {
        return JSON.parse(r);
    } else {
        return null;
    }
}

const sleep = ( milliseconds ) => { return new Promise( resolve => setTimeout( resolve, milliseconds ) ); };

const currentTs = () => { return parseInt( parseInt( Date.now().valueOf() ) / 1000 ); };

async function wait(tx_id, allowed_time = 30000) {
    let start_ts = currentTs();
    while (!isFinished( await getRecord( tx_id ) ) && currentTs() - start_ts < allowed_time) {
        const r = await getRecord(tx_id);
        await sleep(1);
    }
    const r = await getRecord( tx_id );
    console.log(r);
    if( !isFinished( r ) ) {
        return null;
    }
    let rec = await web3.eth.getTransactionReceipt(r.tx_hash);
    return rec;
}

async function main() {
    var account = web3.eth.accounts.create();
    var tx = {
        "to": account.address,
        "value": 1,
    };
    const priority = 5;
    const tx_id = await send(tx, priority)
    const receipt = await wait(tx_id);
    console.log(receipt);
}

main().catch((err) => { console.log(err); });
