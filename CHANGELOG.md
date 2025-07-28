# Changelog

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
