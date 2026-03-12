const API_BASE = '/api/v1';

export async function fetchStatus() {
  // Simulate traffic status for demo
  return Promise.resolve({
    intersections: [
      { id: 1, name: 'A', density_score: 1.2 },
      { id: 2, name: 'B', density_score: 0.7 },
      { id: 3, name: 'C', density_score: 1.7 },
    ],
    status: 'ok',
  });
}

export async function createEmergencyRoute(data) {
  // Simulate success for demo
  return Promise.resolve({ status: 'received' });
}
