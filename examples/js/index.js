'use strict'

const REDIS_URI = process.env.REDIS_URI
const ENDPOINT = process.env.ENDPOINT
const TX_RECORD_EXPIRATION = 24 * 60 * 60 // 1 day
const Redis = require('ioredis')
const redis = new Redis(REDIS_URI)
const Web3 = require('web3')
const web3 = new Web3(ENDPOINT) // your eth network endpoint

const pool = 'transactions'

const genRanHex = size => [...Array(size)].map(() => Math.floor(Math.random() * 16).toString(16)).join('')

const sleep = (milliseconds) => { return new Promise((resolve) => setTimeout(resolve, milliseconds)) }

const currentTs = () => { return parseInt(parseInt(Date.now().valueOf(), 10) / 1000, 10) }

function makeId () {
  const prefix = 'tx-'
  const unique = genRanHex(16)
  return prefix + unique
}

function makeRecord (tx = {}, score) {
  const status = 'PROPOSED'
  return JSON.stringify({
    score: score,
    status: status,
    ...tx
  })
}

function makeScore (priority) {
  const ts = currentTs()
  return priority * Math.pow(10, ts.toString().length) + ts
}

async function send (tx, priority = 5) {
  console.log('Sending tx', tx)
  const id = makeId()
  const score = makeScore(priority)
  const record = makeRecord(tx, score)
  console.log(`Sending score: ${score}, record: ${record}`)
  await redis.multi()
    .set(id, record, 'EX', TX_RECORD_EXPIRATION)
    .zadd(pool, score, id)
    .exec()
  return id
}

function isFinished (record) {
  if (record == null) {
    return null
  }
  const status = 'status' in record ? record.status : null
  return ['SUCCESS', 'FAILED', 'DROPPED'].includes(status)
}

async function getRecord (txId) {
  const r = await redis.get(txId)
  if (r != null) {
    return JSON.parse(r)
  } else {
    return null
  }
}

async function wait (txId, allowedTime = 30000) {
  const startTs = currentTs()
  while (!isFinished(await getRecord(txId)) && currentTs() - startTs < allowedTime) {
    await sleep(1)
  }
  const r = await getRecord(txId)
  if (!isFinished(r)) {
    return null
  }
  const rec = await web3.eth.getTransactionReceipt(r.tx_hash)
  return rec
}

async function main () {
  const account = web3.eth.accounts.create()
  const tx = {
    to: account.address,
    value: 1
  }
  const priority = 5
  const txId = await send(tx, priority)
  const receipt = await wait(txId)
  console.log(receipt)
}

main().catch((err) => { console.log(err) })
