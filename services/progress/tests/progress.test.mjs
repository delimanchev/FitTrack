import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { once } from 'node:events';
import { createServer } from 'node:http';
import { after, before, test } from 'node:test';
import jwt from 'jsonwebtoken';
import { createApp } from '../dist/app.js';

const jwtSecret = 'progress-tests-only-key-at-least-32-bytes';
const date = '2026-11-28';
const weight = { weightKg: 85.5, measuredAt: date };
const bodyMeasurement = { area: 'waist', circumferenceCm: 82, measuredAt: date };
const internalTokens = ['test-goals-token', 'test-exercise-token', 'test-workout-token'];
let lastUserRequest;
let userStub;
let app;
let url;

before(async () => {
  assert.ok(process.env.PROGRESS_TEST_DATABASE_URL, 'Set PROGRESS_TEST_DATABASE_URL to a test database');
  userStub = createServer((request, response) => {
    lastUserRequest = [request.url, request.headers['x-service-token']];
    if (request.headers['x-service-token'] !== 'test-progress-token') {
      response.writeHead(403).end();
    } else if (request.url.startsWith('/users/offline-')) {
      request.socket.destroy();
    } else {
      response.writeHead(request.url.startsWith('/users/missing-') ? 404 : 200).end();
    }
  });
  userStub.listen(0, '127.0.0.1');
  await once(userStub, 'listening');

  Object.assign(process.env, {
    DATABASE_URL: process.env.PROGRESS_TEST_DATABASE_URL,
    JWT_SECRET: jwtSecret,
    JWT_ISSUER: 'fittrack-test',
    JWT_AUDIENCE: 'fittrack-api-test',
    USER_SERVICE_URL: `http://127.0.0.1:${userStub.address().port}`,
    PROGRESS_TO_USER_TOKEN: 'test-progress-token',
    GOALS_TO_PROGRESS_TOKEN: internalTokens[0],
    EXERCISE_TO_PROGRESS_TOKEN: internalTokens[1],
    WORKOUT_TO_PROGRESS_TOKEN: internalTokens[2],
  });
  app = await createApp({ logger: false });
  await app.listen(0, '127.0.0.1');
  url = await app.getUrl();
});

after(async () => {
  await app?.close();
  if (userStub) await new Promise((resolve) => userStub.close(resolve));
});

function bearer(userId, expiresIn = 300) {
  return {
    Authorization: `Bearer ${jwt.sign({}, jwtSecret, {
      subject: userId, issuer: 'fittrack-test', audience: 'fittrack-api-test', expiresIn,
    })}`,
  };
}

async function request(path, method = 'GET', headers = {}, body) {
  const response = await fetch(url + path, {
    method,
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return { status: response.status, data: response.status === 204 ? null : await response.json() };
}

test('weight CRUD, history, and latest use only the signed-in user', async () => {
  const userId = randomUUID();
  const headers = bearer(userId);
  const other = bearer(randomUUID());
  assert.equal((await request('/api/progress/latest', 'GET', headers)).status, 404);

  const first = await request('/api/progress', 'POST', headers, weight);
  assert.equal(first.status, 201);
  assert.deepEqual(lastUserRequest, [`/users/${userId}`, 'test-progress-token']);
  const older = await request('/api/progress', 'POST', headers, { ...weight, measuredAt: '2026-11-27' });
  assert.equal(older.status, 201);
  const page = await request('/api/progress?limit=1&offset=1', 'GET', headers);
  assert.deepEqual(page.data, [older.data]);
  assert.deepEqual((await request('/api/progress', 'GET', other)).data, []);
  assert.deepEqual((await request('/api/progress/latest', 'GET', headers)).data, first.data);

  const path = `/api/progress/${first.data.id}`;
  assert.equal((await request(path, 'PUT', other, weight)).status, 403);
  const updated = await request(path, 'PUT', headers, { ...weight, weightKg: 84 });
  assert.equal(updated.status, 200);
  assert.equal(updated.data.weightKg, 84);
  assert.equal((await request(path, 'DELETE', other)).status, 403);
  assert.equal((await request(path, 'DELETE', headers)).status, 204);
  assert.equal((await request(path, 'DELETE', headers)).status, 404);
  assert.deepEqual((await request('/api/progress/latest', 'GET', headers)).data, older.data);
});

test('body measurements have their own history and CRUD routes', async () => {
  const headers = bearer(randomUUID());
  const base = '/api/progress/body-measurements';
  const created = await request(base, 'POST', headers, bodyMeasurement);
  assert.equal(created.status, 201);
  assert.deepEqual((await request(base, 'GET', headers)).data, [created.data]);
  assert.deepEqual((await request('/api/progress', 'GET', headers)).data, []);
  assert.equal((await request(`/api/progress/${created.data.id}`, 'DELETE', headers)).status, 404);

  const path = `${base}/${created.data.id}`;
  const updated = await request(path, 'PUT', headers, { ...bodyMeasurement, circumferenceCm: 81 });
  assert.equal(updated.status, 200);
  assert.equal(updated.data.circumferenceCm, 81);
  assert.equal((await request(path, 'DELETE', headers)).status, 204);
  assert.deepEqual((await request(base, 'GET', headers)).data, []);
});

test('invalid requests and a failed User check do not insert measurements', async () => {
  const userId = randomUUID();
  const headers = bearer(userId);
  assert.equal((await request('/api/progress')).status, 401);
  assert.equal((await request('/api/progress', 'GET', bearer(userId, -1))).status, 401);
  for (const change of [{ weightKg: 0 }, { weightKg: '88' }, { measuredAt: '2026-02-30' }]) {
    assert.equal((await request('/api/progress', 'POST', headers, { ...weight, ...change })).status, 400);
  }
  assert.equal((await request('/api/progress?limit=0', 'GET', headers)).status, 400);
  for (const [prefix, status] of [['missing-', 404], ['offline-', 503]]) {
    const failedUser = bearer(prefix + userId);
    assert.equal((await request('/api/progress', 'POST', failedUser, weight)).status, status);
    assert.deepEqual((await request('/api/progress', 'GET', failedUser)).data, []);
  }
});

test('all three internal callers can read latest and OpenAPI lists the routes', async () => {
  const userId = randomUUID();
  const created = await request('/api/progress', 'POST', bearer(userId), weight);
  assert.equal(created.status, 201);
  assert.equal((await request('/progress/latest')).status, 403);
  assert.equal((await request('/progress/latest', 'GET', { 'X-Service-Token': internalTokens[0] })).status, 400);
  for (const token of internalTokens) {
    const headers = { 'X-Service-Token': token, 'X-User-Id': userId };
    assert.deepEqual((await request('/progress/latest', 'GET', headers)).data, created.data);
    assert.equal((await request('/progress/latest', 'GET', { ...headers, 'X-User-Id': randomUUID() })).status, 404);
  }
  const { data: schema } = await request('/openapi.json');
  const paths = schema.paths;
  assert.deepEqual(Object.keys(paths['/api/progress']).sort(), ['get', 'post']);
  assert.deepEqual(Object.keys(paths['/api/progress/{id}']).sort(), ['delete', 'put']);
  assert.deepEqual(Object.keys(paths['/api/progress/body-measurements']).sort(), ['get', 'post']);
  assert.deepEqual(Object.keys(paths['/api/progress/body-measurements/{measurementId}']).sort(), ['delete', 'put']);
  assert.ok(paths['/api/progress/latest'].get);
  assert.deepEqual(paths['/progress/latest'].get.security, [{ 'service-token': [] }]);
});
