const test = require('node:test');
const assert = require('node:assert/strict');
const deploy = require('../scripts/deploy_pages.cjs');

function setup(statuses = ['succeed']) {
  const calls = [], outputs = {}, logs = [];
  const core = {getIDToken: async () => 'fake-oidc', setSecret: () => {},
    setOutput: (key, value) => {outputs[key] = value;}, info: value => logs.push(value), warning: value => logs.push(value)};
  const github = {request: async (route, payload) => {
    calls.push({route, payload});
    if (route.endsWith('/cancel')) return {data: {}};
    if (route.startsWith('POST')) return {data: {id: 'deployment-1'}};
    const value = statuses.shift();
    if (value instanceof Error) throw value;
    return {data: {status: value}};
  }};
  return {args: {github, core, context: {repo: {owner: 'owner', repo: 'repo'}, sha: 'abc123'},
    artifactId: '123', siteUrl: 'https://example.com', sleep: async () => {}}, calls, outputs, logs};
}

test('deploys exact upload ID without listing artifacts and waits for public deployment success', async () => {
  const s = setup(['deployment_in_progress', 'succeed']);
  await deploy(s.args);
  assert.equal(s.calls[0].payload.artifact_id, 123);
  assert.equal(s.calls[0].payload.pages_build_version, 'abc123');
  assert.equal(s.calls[0].payload.oidc_token, 'fake-oidc');
  assert.equal(s.calls.length, 3);
  assert.ok(s.calls.every(call => !call.route.includes('/artifacts')));
  assert.deepEqual(s.outputs, {page_url: 'https://example.com', status: 'succeed'});
  assert.ok(s.logs.every(line => !line.includes('fake-oidc')));
});

test('terminal failure cannot publish a success URL', async () => {
  const s = setup(['deployment_content_failed']);
  await assert.rejects(deploy(s.args), /deployment_content_failed/);
  assert.deepEqual(s.outputs, {});
});

test('temporary status API errors retry before reporting success', async () => {
  const s = setup([Object.assign(new Error('temporary'), {status: 502}), 'succeed']);
  await deploy(s.args);
  assert.equal(s.calls.length, 3);
  assert.equal(s.outputs.status, 'succeed');
});

test('timeout cancels the unfinished deployment without publishing success', async () => {
  const s = setup();
  let time = 0;
  await assert.rejects(deploy({...s.args, now: () => time++, timeoutMs: 1}), /timed out/);
  assert.ok(s.calls.at(-1).route.endsWith('/cancel'));
  assert.deepEqual(s.outputs, {});
});

test('creation error never exposes the OIDC request payload', async () => {
  const s = setup();
  s.args.github.request = async () => {throw Object.assign(new Error('fake-oidc'), {status: 403});};
  await assert.rejects(deploy(s.args), error => /HTTP 403/.test(error.message) && !error.message.includes('fake-oidc'));
});

test('missing artifact ID stops before requesting a deployment token', async () => {
  const s = setup();
  s.args.core.getIDToken = async () => {throw new Error('must not request token');};
  await assert.rejects(deploy({...s.args, artifactId: ''}), /invalid Pages artifact ID/);
  assert.equal(s.calls.length, 0);
});
