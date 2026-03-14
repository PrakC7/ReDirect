import React, { useEffect, useState } from "react";

import { createEmergencyRequest, fetchDashboard } from "./api";

const VEHICLE_TYPES = [
  "Ambulance",
  "Police",
  "Fire Brigade",
  "Disaster Response",
  "Other",
];

const PURPOSES = [
  "Medical Emergency",
  "Accident Response",
  "Fire Emergency",
  "Crime Response",
  "Disaster Management",
  "VIP Emergency Movement",
  "Other",
];

const PRIORITIES = ["Critical", "High", "Medium"];
const VEHICLE_ID_TYPES = ["Vehicle Number", "Unit ID", "Department ID"];
const DIRECTION_LABELS = {
  northbound: "Northbound",
  southbound: "Southbound",
  eastbound: "Eastbound",
  westbound: "Westbound",
};
const MOVEMENT_ALIGNMENT_LABELS = {
  "at-zone": "Already at the target zone",
  "towards-zone": "Inbound traffic toward the target zone",
  "cross-traffic": "Mostly cross-traffic around the zone",
  "away-from-zone": "Mostly moving away from the target zone",
  undetermined: "Direction still being inferred",
};

const INITIAL_FORM = {
  requesterName: "",
  department: "",
  vehicleType: "",
  purpose: "",
  otherPurpose: "",
  origin: "",
  destination: "",
  returnDestination: "",
  vehicleIdType: "",
  vehicleId: "",
  priority: "Critical",
  estimatedTravelMinutes: "",
  routeNotes: "",
  declaration: false,
};

function formatTimestamp(value) {
  if (!value) {
    return "Pending";
  }

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDirection(direction) {
  if (!direction) {
    return "Mixed flow";
  }

  return DIRECTION_LABELS[direction] || direction;
}

function formatMovementAlignment(alignment) {
  if (!alignment) {
    return "Direction check pending";
  }

  return MOVEMENT_ALIGNMENT_LABELS[alignment] || alignment;
}

function formatShare(value) {
  if (value == null) {
    return "--";
  }

  return `${Math.round(value * 100)}%`;
}

function MetricCard({ label, value, detail }) {
  return (
    <article className="metric-card">
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
      <span className="metric-detail">{detail}</span>
    </article>
  );
}

function LandingSection({ dashboard, dashboardError, onStart }) {
  const topSignals = dashboard?.intersections ?? [];

  return (
    <section className="panel hero-panel">
      <div className="eyebrow">Municipal traffic prototype</div>
      <h1>ReDirect</h1>
      <p className="hero-copy">
        An AI-assisted traffic optimisation portal that helps city control rooms
        reduce daily junction pressure and create faster green corridors when an
        emergency movement is active.
      </p>

      <div className="chip-row">
        <span className="chip">Adaptive signal timing</span>
        <span className="chip">Direction-aware flow screening</span>
        <span className="chip">Emergency corridor requests</span>
        <span className="chip">20 km nearby junction scan</span>
      </div>

      <div className="metric-grid">
        <MetricCard
          label="Active emergency requests"
          value={dashboard?.active_emergency_count ?? "--"}
          detail="Live requests awaiting or using priority"
        />
        <MetricCard
          label="Average time saved"
          value={
            dashboard ? `${dashboard.average_clearance_gain_minutes} min` : "--"
          }
          detail="Estimated clearance gain per active request"
        />
        <MetricCard
          label="Signal refresh window"
          value={dashboard ? `${dashboard.next_refresh_seconds}s` : "--"}
          detail="How often the dashboard updates recommendations"
        />
      </div>

      <div className="hero-actions">
        <button className="button button-primary" onClick={onStart}>
          Start Emergency Request
        </button>
        <span className="subtle-note">
          For demo use only. Production access remains government-controlled.
        </span>
      </div>

      <div className="section-head">
        <h2>Current signal priorities</h2>
        <span className="subtle-note">
          Ranked by density, incoming flow direction, and corridor importance
        </span>
      </div>

      {dashboardError && <div className="banner error-banner">{dashboardError}</div>}

      <div className="signal-list">
        {topSignals.length > 0 ? (
          topSignals.map((intersection) => (
            <article className="signal-card" key={intersection.id}>
              <div>
                <h3>{intersection.name}</h3>
                <p>
                  {intersection.zone} zone · {intersection.signal_group}
                </p>
                <p className="flow-note">
                  {intersection.primary_inbound_direction
                    ? `${formatDirection(intersection.primary_inbound_direction)} inflow drives ${formatShare(intersection.nearby_inbound_vehicle_share)} of nearby pressure`
                    : "No dominant inbound direction detected in the nearby network yet"}
                </p>
              </div>
              <div className="signal-meta">
                <span className={`status-pill status-${intersection.status.toLowerCase()}`}>
                  {intersection.status}
                </span>
                <strong>{intersection.recommended_green_seconds}s green</strong>
                <span>{intersection.live_vehicle_count} vehicles in queue</span>
                <span>
                  Inbound pressure score {intersection.incoming_pressure_score}
                </span>
              </div>
            </article>
          ))
        ) : (
          <div className="empty-state">
            Loading the current signal plan from the backend dashboard.
          </div>
        )}
      </div>
    </section>
  );
}

function OperationsPanel({ dashboard }) {
  const requests = dashboard?.active_requests ?? [];

  return (
    <aside className="panel sidebar-panel">
      <div className="section-head">
        <h2>Ops Snapshot</h2>
        <span className="subtle-note">
          Auto-refreshed from the backend control service
        </span>
      </div>

      <div className="mini-stat-grid">
        <MetricCard
          label="Intersections tracked"
          value={dashboard?.intersections?.length ?? "--"}
          detail="Sample live corridor network"
        />
        <MetricCard
          label="Direction scan radius"
          value={dashboard ? `${dashboard.priority_radius_km} km` : "--"}
          detail="Nearby junctions checked for inbound traffic flow"
        />
        <MetricCard
          label="Active queue"
          value={requests.length}
          detail="Requests in the emergency priority pool"
        />
      </div>

      <div className="ops-section">
        <h3>Current requests</h3>
        {requests.length > 0 ? (
          <div className="request-list">
            {requests.map((request) => (
              <article className="request-card" key={request.request_id}>
                <div className="request-card-top">
                  <strong>{request.vehicle_type}</strong>
                  <span className="status-pill status-inline">
                    {request.priority}
                  </span>
                </div>
                <p>
                  {request.origin} to {request.destination}
                </p>
                <span>{request.suggested_time_saved_minutes} min estimated gain</span>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            No active emergency requests right now. New requests appear here
            after submission.
          </div>
        )}
      </div>
    </aside>
  );
}

function RequestForm({ dashboard, submitting, submitError, onBack, onSubmit }) {
  const [form, setForm] = useState(INITIAL_FORM);
  const [errors, setErrors] = useState({});

  function handleChange(event) {
    const { name, type, value, checked } = event.target;
    const nextValue = type === "checkbox" ? checked : value;

    setForm((current) => ({
      ...current,
      [name]: nextValue,
    }));

    setErrors((current) => ({
      ...current,
      [name]: "",
    }));
  }

  function validate() {
    const nextErrors = {};

    if (!form.requesterName.trim()) {
      nextErrors.requesterName = "Requester name is required.";
    }
    if (!form.department.trim()) {
      nextErrors.department = "Department or control room is required.";
    }
    if (!form.vehicleType) {
      nextErrors.vehicleType = "Select the emergency vehicle type.";
    }
    if (!form.purpose) {
      nextErrors.purpose = "Select the emergency purpose.";
    }
    if (form.purpose === "Other" && !form.otherPurpose.trim()) {
      nextErrors.otherPurpose = "Specify the emergency purpose.";
    }
    if (!form.origin.trim()) {
      nextErrors.origin = "Origin location is required.";
    }
    if (!form.destination.trim()) {
      nextErrors.destination = "Destination location is required.";
    }
    if (!form.vehicleIdType) {
      nextErrors.vehicleIdType = "Select an identification type.";
    }
    if (!form.vehicleId.trim()) {
      nextErrors.vehicleId = "Vehicle identification is required.";
    }
    if (!form.estimatedTravelMinutes) {
      nextErrors.estimatedTravelMinutes = "Enter the estimated travel time.";
    }
    if (!form.declaration) {
      nextErrors.declaration =
        "You must confirm that this request is for an active emergency.";
    }

    return nextErrors;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = validate();
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    await onSubmit({
      ...form,
      purpose: form.purpose === "Other" ? form.otherPurpose.trim() : form.purpose,
      estimatedTravelMinutes: Number(form.estimatedTravelMinutes),
    });
  }

  return (
    <section className="page-grid form-layout">
      <div className="panel form-panel">
        <div className="section-head">
          <h2>Create emergency priority corridor</h2>
          <span className="subtle-note">
            Submit only authorized requests for real incidents
          </span>
        </div>

        <form className="request-form" onSubmit={handleSubmit} noValidate>
          <div className="field-grid">
            <label className="field">
              <span>Requester name</span>
              <input
                name="requesterName"
                value={form.requesterName}
                onChange={handleChange}
                placeholder="Control room operator"
              />
              {errors.requesterName && (
                <small className="field-error">{errors.requesterName}</small>
              )}
            </label>

            <label className="field">
              <span>Department</span>
              <input
                name="department"
                value={form.department}
                onChange={handleChange}
                placeholder="Ambulance command / police HQ"
              />
              {errors.department && (
                <small className="field-error">{errors.department}</small>
              )}
            </label>

            <label className="field">
              <span>Vehicle type</span>
              <select
                name="vehicleType"
                value={form.vehicleType}
                onChange={handleChange}
              >
                <option value="">Select vehicle type</option>
                {VEHICLE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
              {errors.vehicleType && (
                <small className="field-error">{errors.vehicleType}</small>
              )}
            </label>

            <label className="field">
              <span>Emergency purpose</span>
              <select name="purpose" value={form.purpose} onChange={handleChange}>
                <option value="">Select purpose</option>
                {PURPOSES.map((purpose) => (
                  <option key={purpose} value={purpose}>
                    {purpose}
                  </option>
                ))}
              </select>
              {errors.purpose && (
                <small className="field-error">{errors.purpose}</small>
              )}
            </label>

            {form.purpose === "Other" && (
              <label className="field field-span">
                <span>Specify purpose</span>
                <input
                  name="otherPurpose"
                  value={form.otherPurpose}
                  onChange={handleChange}
                  placeholder="Explain the special movement"
                />
                {errors.otherPurpose && (
                  <small className="field-error">{errors.otherPurpose}</small>
                )}
              </label>
            )}

            <label className="field">
              <span>Origin</span>
              <input
                name="origin"
                value={form.origin}
                onChange={handleChange}
                placeholder="AIIMS Trauma Centre"
              />
              {errors.origin && (
                <small className="field-error">{errors.origin}</small>
              )}
            </label>

            <label className="field">
              <span>Destination</span>
              <input
                name="destination"
                value={form.destination}
                onChange={handleChange}
                placeholder="Safdarjung Hospital"
              />
              {errors.destination && (
                <small className="field-error">{errors.destination}</small>
              )}
            </label>

            <label className="field">
              <span>Return destination</span>
              <input
                name="returnDestination"
                value={form.returnDestination}
                onChange={handleChange}
                placeholder="Optional"
              />
            </label>

            <label className="field">
              <span>Vehicle ID type</span>
              <select
                name="vehicleIdType"
                value={form.vehicleIdType}
                onChange={handleChange}
              >
                <option value="">Select ID type</option>
                {VEHICLE_ID_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
              {errors.vehicleIdType && (
                <small className="field-error">{errors.vehicleIdType}</small>
              )}
            </label>

            <label className="field">
              <span>Vehicle ID</span>
              <input
                name="vehicleId"
                value={form.vehicleId}
                onChange={handleChange}
                placeholder="DL 01 XX 1234"
              />
              {errors.vehicleId && (
                <small className="field-error">{errors.vehicleId}</small>
              )}
            </label>

            <label className="field">
              <span>Priority</span>
              <select name="priority" value={form.priority} onChange={handleChange}>
                {PRIORITIES.map((priority) => (
                  <option key={priority} value={priority}>
                    {priority}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Estimated travel time (minutes)</span>
              <input
                min="1"
                max="180"
                name="estimatedTravelMinutes"
                type="number"
                value={form.estimatedTravelMinutes}
                onChange={handleChange}
                placeholder="12"
              />
              {errors.estimatedTravelMinutes && (
                <small className="field-error">
                  {errors.estimatedTravelMinutes}
                </small>
              )}
            </label>

            <label className="field field-span">
              <span>Route notes</span>
              <textarea
                name="routeNotes"
                value={form.routeNotes}
                onChange={handleChange}
                placeholder="Optional notes for route control staff"
                rows="3"
              />
            </label>
          </div>

          <label className="checkbox-field">
            <input
              checked={form.declaration}
              name="declaration"
              onChange={handleChange}
              type="checkbox"
            />
            <span>
              I confirm this request represents an active, authorized emergency
              movement.
            </span>
          </label>
          {errors.declaration && (
            <small className="field-error">{errors.declaration}</small>
          )}

          {submitError && <div className="banner error-banner">{submitError}</div>}

          <div className="button-row">
            <button
              className="button button-secondary"
              onClick={onBack}
              type="button"
            >
              Back
            </button>
            <button className="button button-primary" disabled={submitting} type="submit">
              {submitting ? "Submitting..." : "Activate Priority Corridor"}
            </button>
          </div>
        </form>
      </div>

      <OperationsPanel dashboard={dashboard} />
    </section>
  );
}

function ConfirmationPanel({ dashboard, record, onReset }) {
  return (
    <section className="page-grid confirmation-layout">
      <div className="panel confirmation-panel">
        <div className="confirmation-badge">Request accepted</div>
        <h2>{record.request_id}</h2>
        <p className="hero-copy">
          {record.vehicle_type} priority has been registered from {record.origin} to{" "}
          {record.destination}. The backend generated a staged green corridor on
          top of the same direction-aware traffic model used for the live
          network snapshot.
        </p>

        <div className="metric-grid">
          <MetricCard
            label="Status"
            value={record.status}
            detail="Control room workflow state"
          />
          <MetricCard
            label="Estimated time saved"
            value={`${record.suggested_time_saved_minutes} min`}
            detail="Based on priority and live corridor demand"
          />
          <MetricCard
            label="Corridor window"
            value={`${record.corridor_window_seconds}s`}
            detail="Green window applied per intersection"
          />
          <MetricCard
            label="Direction screen"
            value={`${record.priority_radius_km} km`}
            detail="Nearby inbound traffic is checked before sequencing"
          />
        </div>

        <div className="section-head">
          <h3>Generated corridor sequence</h3>
          <span className="subtle-note">
            Submitted at {formatTimestamp(record.submitted_at)}
          </span>
        </div>

        <div className="timeline">
          {record.corridor.map((step) => (
            <article className="timeline-item" key={`${record.request_id}-${step.intersection_id}`}>
              <div className="timeline-dot" />
              <div className="timeline-content">
                <strong>{step.intersection_name}</strong>
                <span>
                  {formatTimestamp(step.green_from)} to {formatTimestamp(step.green_to)}
                </span>
                <span className="timeline-detail">
                  {step.priority_phase === "radius-first"
                    ? "Within the nearby priority radius"
                    : "Handled after nearby intersections"}{" "}
                  | {formatMovementAlignment(step.movement_alignment)}
                  {step.target_flow_direction
                    ? ` | ${formatDirection(step.target_flow_direction)} flow checked`
                    : ""}
                  {step.approaching_vehicle_share != null
                    ? ` | ${formatShare(step.approaching_vehicle_share)} inbound share`
                    : ""}
                </span>
              </div>
            </article>
          ))}
        </div>

        <div className="button-row">
          <button className="button button-primary" onClick={onReset}>
            Plan Another Request
          </button>
        </div>
      </div>

      <OperationsPanel dashboard={dashboard} />
    </section>
  );
}

export default function App() {
  const [screen, setScreen] = useState("landing");
  const [dashboard, setDashboard] = useState(null);
  const [dashboardError, setDashboardError] = useState("");
  const [record, setRecord] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      try {
        const snapshot = await fetchDashboard();
        if (!cancelled) {
          setDashboard(snapshot);
          setDashboardError("");
        }
      } catch (error) {
        if (!cancelled) {
          setDashboardError(error.message);
        }
      }
    }

    loadDashboard();
    const intervalId = window.setInterval(loadDashboard, 30000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  async function handleCreateRequest(formValues) {
    try {
      setSubmitting(true);
      setSubmitError("");
      const createdRecord = await createEmergencyRequest(formValues);
      setRecord(createdRecord);
      setScreen("confirmation");
      const refreshedDashboard = await fetchDashboard();
      setDashboard(refreshedDashboard);
      setDashboardError("");
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  function resetFlow() {
    setScreen("landing");
    setRecord(null);
    setSubmitError("");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">Smart traffic optimisation prototype</span>
          <strong>Emergency Traffic Priority Request Portal</strong>
        </div>
        <span className="subtle-note">FastAPI + React demo workflow</span>
      </header>

      {screen === "landing" && (
        <div className="page-grid">
          <LandingSection
            dashboard={dashboard}
            dashboardError={dashboardError}
            onStart={() => setScreen("form")}
          />
          <OperationsPanel dashboard={dashboard} />
        </div>
      )}

      {screen === "form" && (
        <RequestForm
          dashboard={dashboard}
          onBack={() => setScreen("landing")}
          onSubmit={handleCreateRequest}
          submitError={submitError}
          submitting={submitting}
        />
      )}

      {screen === "confirmation" && record && (
        <ConfirmationPanel
          dashboard={dashboard}
          onReset={resetFlow}
          record={record}
        />
      )}
    </div>
  );
}
