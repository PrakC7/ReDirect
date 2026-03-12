const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Request failed. Please try again.");
  }

  return data;
}

export function fetchDashboard() {
  return request("/dashboard");
}

export function createEmergencyRequest(data) {
  return request("/emergency/requests", {
    method: "POST",
    body: JSON.stringify({
      requester_name: data.requesterName,
      department: data.department,
      vehicle_type: data.vehicleType,
      purpose: data.purpose,
      origin: data.origin,
      destination: data.destination,
      return_destination: data.returnDestination || null,
      vehicle_id_type: data.vehicleIdType,
      vehicle_id: data.vehicleId,
      priority: data.priority,
      estimated_travel_minutes: data.estimatedTravelMinutes,
      route_notes: data.routeNotes || null,
    }),
  });
}
