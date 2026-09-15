# Service Level Objective — service-a `/greet`

## SLI (Service Level Indicator)
Proportion of requests to `/greet` that return HTTP 2xx status within 300ms.

## SLO (Service Level Objective)
99% of requests meet the SLI, measured over a rolling 7-day window.

## Error Budget
Window = 7 days = 168 hours = 10,080 minutes
SLO = 99% -> allowed failure rate = 1% = 0.01
Error budget = 0.01 x 10,080 minutes = 100.8 minutes/week

## Measurement queries (PromQL)

Success ratio:
sum(rate(http_requests_total{route="/greet",status=~"2.."}[5m]))
/
sum(rate(http_requests_total{route="/greet"}[5m]))

Latency ratio (requests under 300ms):
sum(rate(http_request_duration_seconds_bucket{route="/greet",le="0.3"}[5m]))
/
sum(rate(http_request_duration_seconds_count{route="/greet"}[5m]))

p95 latency:
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{route="/greet"}[5m])) by (le))

## Alerting

A `PrometheusRule` (`HighErrorBudgetBurn`) watches the same success-ratio query at a 14.4x burn-rate threshold — the standard "fast burn" threshold from Google's SRE workbook, corresponding to exhausting a 7-day error budget in ~12 hours. It requires the threshold to be breached continuously for 5 minutes (`for: 5m`) before firing, to avoid alerting on brief blips.

Alertmanager routes firing alerts to a Slack channel (`#alerts`) via an incoming webhook, with `send_resolved: true` so the channel also gets a resolved notification once the burn rate drops back to normal.

**Verified end-to-end**, not just configured: service-b was temporarily patched to fail 60% of requests, sustained failing traffic was generated for 5+ minutes, and the alert genuinely fired and posted to Slack with the real SLO description text - not a synthetic test alert. The chaos code was then reverted.

## Known limitations / lessons learned

- **Image tags matter.** Early in this sprint, images were pushed under the floating `:latest` tag. Kubernetes' pull-caching behavior (and a brief Docker Hub CDN propagation delay after pushing) meant new builds sometimes didn't actually reach running pods despite a successful `kubectl rollout restart`. Switching to versioned tags (`v1-metrics`, `v2-logging`, etc.) made every deploy unambiguous and traceable to an exact build. In a production pipeline, this would be automated via CI tagging images with the Git SHA.

- **A Service's labels and its selector are not the same thing.** Prometheus's ServiceMonitor mechanism matches on a Service object's own `metadata.labels`, not on `spec.selector` (which only controls traffic routing to pods). Both Service manifests here were missing `metadata.labels`, which caused Prometheus to silently drop all scrape targets for both services for several hours of otherwise-correct setup - despite the ServiceMonitor objects, the app instrumentation, and the routing all being correct individually. Root-caused by comparing Prometheus's raw relabel_configs against the actual discovered labels via its own `/api/v1/targets` API.

- **Helm list values fully replace, they don't merge.** Using `helm upgrade --reuse-values` with a new `receivers` list silently deleted the kube-prometheus-stack chart's default `null` receiver (used to route the harmless `Watchdog` heartbeat alert), breaking Alertmanager until the `null` receiver was explicitly re-added alongside the new Slack receiver.
