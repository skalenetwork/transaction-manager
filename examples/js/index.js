'use strict';

const Redis = require("ioredis");
const redis = new Redis();
var Web3 = require('web3');
var web3 = new Web3('http://127.0.0.1:8545'); // your eth network endpoint

const pool = 'transactions'

const genRanHex = size => [...Array(size)].map(() => Math.floor(Math.random() * 16).toString(16)).join('');

function make_id() {
    const prefix = 'tx-';
    const timeHex = Date.now().toString(16);
    const unique = genRanHex(12);
    return prefix + timeHex + unique;
}

function make_record(tx = {}, priority = 1) {
    const status = 'PROPOSED';
    return JSON.stringify({
        'priority': priority,
        'status': status,
        ...tx
    });
}

async function send(tx, priority) {
    console.log(`Sending tx ${tx}`)
    var id = make_id();
    var record = make_record(tx, priority);
    console.log(id, record);
    await redis.multi()
        .set(id, record)
        .zadd(pool, priority, id)
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
    const priority = 1;
    const tx_id = await send(tx, priority)
    const wait_timeout = 100;
    const receipt = await wait(tx_id);
    console.log(receipt);
}

main().catch((err) => { console.log(err); });
