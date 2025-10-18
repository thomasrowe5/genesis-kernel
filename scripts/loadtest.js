import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
  vus: 5,
  duration: '30s',
};

export default function () {
  const payload = JSON.stringify({
    task_type: 'sleep',
    args: [],
    kwargs: { seconds: 0.1 },
  });
  const headers = { 'Content-Type': 'application/json' };
  const res = http.post('http://localhost:8000/jobs', payload, { headers });
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(0.5);
}
