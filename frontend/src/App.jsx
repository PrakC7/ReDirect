import React, { useState } from "react";

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
const VEHICLE_ID_TYPES = [
  "Vehicle Number",
  "Unit ID",
  "Department ID"
];

function Landing({ onStart }) {
  return (
    <div className="landing">
      <h1>Emergency Traffic Priority Request Portal</h1>
      <p>
        This portal demonstrates how an AI-powered traffic system can dynamically adjust signals to give priority to emergency vehicles, reducing response times and saving lives.
      </p>
      <div className="notice">
        <b>Notice:</b> Access to this system requires government authorization. This prototype is created only to demonstrate the concept.
      </div>
      <button className="cta" onClick={onStart}>
        Request Traffic Priority
      </button>
    </div>
  );
}

function RequestForm({ onSubmit }) {
  const [vehicleType, setVehicleType] = useState("");
  const [purpose, setPurpose] = useState("");
  const [otherPurpose, setOtherPurpose] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [backTo, setBackTo] = useState("");
  const [vehicleIdType, setVehicleIdType] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [priority, setPriority] = useState("");
  const [travelTime, setTravelTime] = useState("");
  const [routeDesc, setRouteDesc] = useState("");
  const [declared, setDeclared] = useState(false);
  const [touched, setTouched] = useState({});
  const [error, setError] = useState("");

  const showOtherPurpose = purpose === "Other";

  function validate() {
    if (!vehicleType) return "Vehicle Type is required.";
    if (!purpose) return "Emergency Purpose is required.";
    if (purpose === "Other" && !otherPurpose.trim()) return "Specify Purpose is required.";
    if (!from.trim()) return "Origin Location is required.";
    if (!to.trim()) return "Destination Location is required.";
    if (!vehicleIdType) return "Vehicle Identification type is required.";
    if (!vehicleId.trim()) return "Vehicle Identification is required.";
    if (!priority) return "Priority Level is required.";
    if (!travelTime.trim()) return "Estimated Travel Time is required.";
    if (!declared) return "You must confirm the declaration.";
    return "";
  }

  function handleSubmit(e) {
    e.preventDefault();
    setTouched({
      vehicleType: true,
      purpose: true,
      otherPurpose: true,
      from: true,
      to: true,
      vehicleIdType: true,
      vehicleId: true,
      priority: true,
      travelTime: true,
      declared: true,
    });
    const err = validate();
    setError(err);
    if (!err) {
      onSubmit({
        vehicleType,
        purpose: purpose === "Other" ? otherPurpose : purpose,
        from,
        to,
        backTo,
        vehicleIdType,
        vehicleId,
        priority,
        travelTime,
        routeDesc,
      });
    }
  }

  function markTouched(field) {
    setTouched((t) => ({ ...t, [field]: true }));
  }

  return (
    <form className="request-form" onSubmit={handleSubmit} autoComplete="off">
      <h2>Request Traffic Signal Priority</h2>
      <div className="form-row">
        <label>Vehicle Type<span>*</span></label>
        <select value={vehicleType} onChange={e => setVehicleType(e.target.value)} onBlur={() => markTouched("vehicleType")}> 
          <option value="">Select</option>
          {VEHICLE_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
        {touched.vehicleType && !vehicleType && <div className="error">Required</div>}
      </div>
      <div className="form-row">
        <label>Purpose<span>*</span></label>
        <select value={purpose} onChange={e => setPurpose(e.target.value)} onBlur={() => markTouched("purpose")}> 
          <option value="">Select</option>
          {PURPOSES.map((purpose) => (
            <option key={purpose} value={purpose}>
              {purpose}
            </option>
          ))}
        </select>
        {touched.purpose && !purpose && <div className="error">Required</div>}
      </div>
      {showOtherPurpose && (
        <div className="form-row">
          <label>Specify Purpose</label>
          <input type="text" value={otherPurpose} onChange={e => setOtherPurpose(e.target.value)} onBlur={() => markTouched("otherPurpose")}/>
        </div>
      )}
      <div className="form-row">
        <label>From<span>*</span></label>
        <input type="text" value={from} onChange={e => setFrom(e.target.value)} onBlur={() => markTouched("from")}/>
      </div>
      <div className="form-row">
        <label>To<span>*</span></label>
        <input type="text" value={to} onChange={e => setTo(e.target.value)} onBlur={() => markTouched("to")}/>
      </div>
      <div className="form-row">
        <label>Back to<span>*</span></label>
        <input type="text" value={backTo} onChange={e => setBackTo(e.target.value)} onBlur={() => markTouched("backTo")}/>
      </div>
      <div className="form-row">
        <label>Vehicle ID Type<span>*</span></label>
        <select value={vehicleIdType} onChange={e => setVehicleIdType(e.target.value)} onBlur={() => markTouched("vehicleIdType")}> 
          <option value="">Select</option>
          {VEHICLE_ID_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
        {touched.vehicleIdType && !vehicleIdType && <div className="error">Required</div>}
      </div>
      <div className="form-row">
        <label>Vehicle ID<span>*</span></label>
        <input type="text" value={vehicleId} onChange={e => setVehicleId(e.target.value)} onBlur={() => markTouched("vehicleId")}/>
      </div>
      <div className="form-row">
        <label>Priority Level<span>*</span></label>
        <select value={priority} onChange={e => setPriority(e.target.value)} onBlur={() => markTouched("priority")}> 
          <option value="">Select</option>
          {PRIORITIES.map((priority) => (
            <option key={priority} value={priority}>
              {priority}
            </option>
          ))}
        </select>
        {touched.priority && !priority && <div className="error">Required</div>}
      </div>
      <div className="form-row">
        <label>Estimated Travel Time<span>*</span></label>
        <input type="text" value={travelTime} onChange={e => setTravelTime(e.target.value)} onBlur={() => markTouched("travelTime")}/>
      </div>
      <div className="form-row">
        <label>Route Description</label>
        <input type="text" value={routeDesc} onChange={e => setRouteDesc(e.target.value)}/>
      </div>
      <div className="form-row">
        <label>Declared</label>
        <input type="checkbox" checked={declared} onChange={e => setDeclared(e.target.checked)}/>
      </div>
      <button type="submit">Submit Request</button>
      {error && <div>{error}</div>}
    </form>
  );
}

function Simulation({ onReset }) {
  // Simple traffic signal animation
  const [step, setStep] = useState(0);
  React.useEffect(() => {
    if (step < 3) {
      const t = setTimeout(() => setStep(step + 1), 900);
      return () => clearTimeout(t);
    }
  }, [step]);
  return (
    <div className="simulation">
      <h2>Emergency Request Accepted</h2>
      <p>AI Traffic System Activated</p>
      <div className="signal-row">
        <div className={`signal ${step >= 1 ? "green" : ""}`}></div>
        <div className={`signal ${step >= 2 ? "green" : ""}`}></div>
        <div className={`signal ${step >= 3 ? "green" : ""}`}></div>
      </div>
      <div className="route-anim">
        <div className="car" style={{ left: `${step * 33}%` }} />
        <div className="route-bar" />
      </div>
      <p className="success-msg">Traffic signals along your route have been prioritized for emergency passage.</p>
      <button className="cta" onClick={onReset}>Submit Another Request</button>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState("landing");
  return (
    <div className="portal-bg">
      {page === "landing" && <Landing onStart={() => setPage("form")} />}
      {page === "form" && <RequestForm onSubmit={() => setPage("sim")} />}
      {page === "sim" && <Simulation onReset={() => setPage("landing")} />}
      <footer>
        <small>
          &copy; {new Date().getFullYear()} Emergency Traffic Priority Prototype. For demonstration only.
        </small>
      </footer>
    </div>
  );
}
