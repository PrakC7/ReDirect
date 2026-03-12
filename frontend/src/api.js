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
  // Map frontend data to backend EmergencyVehicle model
  const payload = {
    id: Date.now(),
    type: data.vehicleType,
    location: data.from,
    timestamp: new Date().toISOString(),
    // Optionally, add more fields if backend expects them
  };
  const res = await fetch(`${API_BASE}/emergency/alert`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error('Failed to submit emergency request');
  }
  return res.json();
}
