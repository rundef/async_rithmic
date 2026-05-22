# Changelog

## [1.6.1] - 2026-05-22
### Added
- Order: added support for retrieving fill history between two timestamps.
- Order: added support for replaying past executions through `on_exchange_order_notification` callbacks.

## [1.6.0] - 2026-05-10
### Added
- Added support for repository plant connections.
- Added support for overriding `plant_connect_delay`, the sleep duration between plant connection attempts.
- Order: added support for market-on-reject for bracket stop-loss orders.
- Order: added trailing stop support.

### Changed
- Regenerated protobuf files for Rithmic API version 0.89.0.0.
- History: improved historical replay request tracking.
- History: handle Rithmic replay truncation by issuing additional replay requests until returned data reaches `end_time`.

### Fixed
- Fixed initial reconnection attempt ignoring reconnection settings.
- Ticker: raise on empty `get_front_month_contract` response. Thanks [@olivier-babelcast](https://github.com/olivier-babelcast).


## [1.5.10] - 2026-04-20
### Fixed
- History: per-request events to avoid KeyError + shared-event race (by [@olivier-babelcast](https://github.com/olivier-babelcast))

## [1.5.9] - 2026-02-20
### Added
- Allow passing order object to modify_order() to skip get_order() call (by [@briandecamp](https://github.com/briandecamp))

## [1.5.8] - 2026-02-08
### Fixed
- Handle rpCode '7' (no data) as empty result instead of error (by [@olivier-babelcast](https://github.com/olivier-babelcast))

## [1.5.7] - 2025-12-01
### Added
- Support for specifying OrderPlacement mode (manual or auto) (by [@dhsmyth](https://github.com/dhsmyth))

## [1.5.6] - 2025-11-12
### Added
- Allow connection to a subset of plants only

## [1.5.5] - 2025-08-23
### Fixed
- Bug for timestamps with leading zeros for microseconds (by [@briandecamp](https://github.com/briandecamp))

## [1.5.4] - 2025-07-28
### Added
- Order book/market depth methods

## [1.5.3] - 2025-07-09
### Added
- Logger name suffix kwarg

### Fixed
- Stop background tasks when connection to a plant fails

## [1.5.2] - 2025-07-04
### Added
- PNL updates subscriptions
- Documentation for Account PNL snapshot request
- Conformance script

## [1.5.1] - 2025-06-25
- Adjust websocket ping timeout

## [1.5.0] - 2025-06-17
### Removed
The `gateway` parameter has been removed from `RithmicClient.__init__()`.

Use the `url` parameter to specify the connection endpoint.

## [1.4.5] - 2025-06-14

### Deprecated
- `gateway` parameter in `RithmicClient.__init__()` is deprecated in favor of `url`.

## [1.4.4] - 2025-06-10

### Fixed
- Tweak WebSocket ping/timeout to reduce disconnections.
- Fix: event handlers shouldn't be shared across all instances of RithmicClient

## [1.4.3] - 2025-06-05

### Added
- Automatically resubscribe to market data after connection loss and reconnection

## [1.4.2] - 2025-06-05
### Fixed
- Fix: avoid duplicate reconnects on websocket disconnect

### Added
- Improve logging for lock acquisition timeouts

## [1.4.1] - 2025-05-21
### Added
- Added retries
- Added documentation for the `order` plant
- Various improvement in the `order` plant
