import React from "react";

export function MetricCard({
  title,
  value,
  subvalue = null,
  statusBadge = null,
  statusTone = "neutral", // "safe", "warning", "danger", "neutral"
  description = null,
  metaDetails = [],
  tags = [],
  note = null,
}) {
  const toneMap = {
    safe: "card-tone-safe",
    warning: "card-tone-warning",
    danger: "card-tone-danger",
    neutral: "card-tone-neutral",
  };

  return (
    <div className={`intel-card ${toneMap[statusTone] || "card-tone-neutral"}`}>
      <div className="intel-card-head">
        <h3 className="intel-card-title">{title}</h3>
        {statusBadge && <span className="intel-status-pill">{statusBadge}</span>}
      </div>

      <div className="intel-primary-metric">
        <div className="intel-main-val">{value}</div>
        {subvalue && <div className="intel-sub-val">{subvalue}</div>}
      </div>

      {description && <p className="intel-description">{description}</p>}

      {tags && tags.length > 0 && (
        <div className="intel-tags-row">
          {tags.map((tag, idx) => (
            <span key={idx} className={`intel-tag-pill tag-sev-${tag.severity?.toLowerCase() || "medium"}`}>
              {tag.label || tag}
            </span>
          ))}
        </div>
      )}

      {metaDetails && metaDetails.length > 0 && (
        <div className="intel-meta-list">
          {metaDetails.map((item, idx) => (
            <div key={idx} className="intel-meta-item">
              <span className="meta-k">{item.label}:</span>
              <span className="meta-v">{item.value}</span>
            </div>
          ))}
        </div>
      )}

      {note && (
        <div className="intel-card-foot">
          <span>{note}</span>
        </div>
      )}
    </div>
  );
}
