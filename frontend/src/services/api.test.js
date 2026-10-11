import test from 'node:test';
import assert from 'node:assert/strict';
import {request} from './api.js';

test('timeout is actionable but user cancellation stays AbortError', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async (url,{signal}) => new Promise((resolve,reject) => signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError')),{once:true}));
  try {
    await assert.rejects(request('/test',{timeout:5}), /timed out/);
    const ctl = new AbortController(); ctl.abort();
    await assert.rejects(request('/test',{signal:ctl.signal}), {name:'AbortError'});
  } finally {globalThis.fetch=original;}
});
test('late response after cancellation cannot become a successful result', async () => {
  const original = globalThis.fetch;
  const ctl = new AbortController();
  globalThis.fetch = async () => ({ok:true,json:async()=> {ctl.abort();return {stale:true};}});
  try {await assert.rejects(request('/test',{signal:ctl.signal}),{name:'AbortError'});}
  finally {globalThis.fetch=original;}
});
