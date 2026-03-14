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
      origin_latitude: Number(data.originLatitude),
      origin_longitude: Number(data.originLongitude),
      origin_location_source: data.originLocationSource,
      destination: data.destination,
      destination_latitude: Number(data.destinationLatitude),
      destination_longitude: Number(data.destinationLongitude),
      destination_location_source: data.destinationLocationSource,
      return_destination: data.returnDestination || null,
      return_destination_latitude: data.returnDestinationLatitude
        ? Number(data.returnDestinationLatitude)
        : null,
      return_destination_longitude: data.returnDestinationLongitude
        ? Number(data.returnDestinationLongitude)
        : null,
      return_destination_location_source:
        data.returnDestinationLocationSource || null,
      vehicle_id_type: data.vehicleIdType,
      vehicle_id: data.vehicleId,
      priority: data.priority,
      estimated_travel_minutes: data.estimatedTravelMinutes,
      route_notes: data.routeNotes || null,
    }),
  });
}

export function approveEmergencyRequest(requestId, data) {
  return request(`/emergency/requests/${requestId}/approve`, {
    method: "POST",
    headers: {
      "X-API-Key": data.apiKey,
    },
    body: JSON.stringify({
      route_id: data.routeId,
      controller_name: data.controllerName,
      controller_role: data.controllerRole,
      approval_method: "camera-verified",
      camera_reference: data.cameraReference,
      signal_override_authorized: true,
    }),
  });
}
