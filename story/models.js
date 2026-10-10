// Pure functions shared by the browser story and its tests.
// They mirror story/generator/scenario.py exactly (same standardisation and softmax).

export function softmax(z) {
  const m = Math.max(...z);
  const e = z.map((x) => Math.exp(x - m));
  const s = e.reduce((a, b) => a + b, 0);
  return e.map((x) => x / s);
}

export function predict(model, x) {
  const xs = x.map((v, j) => (v - model.mean[j]) / model.scale[j]);
  return softmax(model.bias.map((b, c) => model.weights[c].reduce((acc, w, j) => acc + w * xs[j], b)));
}

export function featureVector(model, features) {
  return model.features.map((name) => {
    if (!(name in features)) throw new Error(`Missing feature ${name}`);
    return features[name];
  });
}

export function parameterCount(model) {
  return model.weights.length * (model.weights[0].length + 1);
}

/** Wilson score interval for a binomial proportion (95% by default). */
export function wilson(successes, n, z = 1.959964) {
  if (n === 0) return [0, 0];
  const p = successes / n;
  const denom = 1 + (z * z) / n;
  const centre = (p + (z * z) / (2 * n)) / denom;
  const half = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / denom;
  return [centre - half, centre + half];
}

/** Route-3 escalation rule: accept the compact model only if its top probability clears the threshold. */
export function escalationDecision(compactProbs, threshold) {
  const top = Math.max(...compactProbs);
  return { top, index: compactProbs.indexOf(top), escalate: top < threshold };
}

/**
 * Time per call in microseconds: median over `batches` batches of `perBatch` calls.
 * Batching is needed because browsers coarsen performance.now() (often to 0.1 ms).
 */
export function microsPerCall(fn, perBatch = 20000, batches = 5, now = () => performance.now()) {
  const samples = [];
  let sink = 0;
  for (let b = 0; b < batches; b++) {
    const t0 = now();
    for (let i = 0; i < perBatch; i++) {
      const r = fn();
      sink += Array.isArray(r) ? r[0] : r ? 1 : 0;
    }
    samples.push(((now() - t0) * 1000) / perBatch);
  }
  samples.sort((a, b) => a - b);
  if (Number.isNaN(sink)) throw new Error("unreachable");
  return samples[Math.floor(samples.length / 2)];
}
