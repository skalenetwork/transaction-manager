'use strict';

const REDIS_URI = process.env.REDIS_URI
const ENDPOINT = process.env.ENDPOINT
const Redis = require("ioredis");
const redis = new Redis(REDIS_URI);
var Web3 = require('web3');
var web3 = new Web3(ENDPOINT); // your eth network endpoint

const pool = 'transactions'

const genRanHex = size => [...Array(size)].map(() => Math.floor(Math.random() * 16).toString(16)).join('');

function make_id() {
    const prefix = 'tx-';
    const unique = genRanHex(16);
    return prefix + unique;
}

function make_record(tx = {}, score) {
    const status = 'PROPOSED';
    return JSON.stringify({
        'score': score,
        'status': status,
        ...tx
    });
}

function make_score(priority) {
    const ts = parseInt(Date.now() / 1000)
    return priority * Math.pow(10, ts.toString().length) + ts;
}

async function send(tx, priority = 5) {
    console.log('Sending tx', tx)
    var id = make_id();
    var score = make_score(priority)
    var record = make_record(tx, score);
    console.log(`Sending score: ${score}, record: ${record}`)
    await redis.multi()
        .set(id, record)
        .zadd(pool, score, id)
        .exec();
    return id;
}

function is_finished(record) {
    if (record == null) {
        return null;
    }
    const status = 'status' in record ? record['status'] : null;
    return ['SUCCESS', 'FAILED', 'DROPPED'].includes(status);
}

async function get_record(tx_id) {
    const r = await redis.get(tx_id);
    if (r != null) {
        return JSON.parse(r);
    } else {
        return null;
    }
}

async function wait(tx_id) {
    console.log(tx_id);
    var hash;
    while (hash === undefined) {
        var r = await get_record(tx_id)
        if (is_finished(r)) {
            hash = r['tx_hash'];
        }
    }
    console.log('Hash', hash);
    return await web3.eth.getTransactionReceipt(hash);
}

async function main() {
    var account = web3.eth.accounts.create();
    var tx = {
        'to': account.address,
        'value': 1,
    };
    const priority = 5;
    const tx_id = await send(tx, priority)
    const receipt = await wait(tx_id);
    console.log(receipt);
}

main().catch((err) => { console.log(err); });
