# Python Rithmic API

[![PyPI - Version](https://img.shields.io/pypi/v/async_rithmic)](https://pypi.org/project/async-rithmic/)
[![CI](https://github.com/rundef/async_rithmic/actions/workflows/ci.yml/badge.svg)](https://github.com/rundef/async_rithmic/actions/workflows/ci.yml)
[![Documentation](https://app.readthedocs.org/projects/async-rithmic/badge/?version=latest)](https://async-rithmic.readthedocs.io/en/latest/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/async_rithmic)](https://pypistats.org/packages/async-rithmic)

A robust, async-based Python API designed to interface seamlessly with the Rithmic Protocol Buffer API. This package is built to provide an efficient and reliable connection to Rithmic's trading infrastructure, catering to advanced trading strategies and real-time data handling.

This was originally a fork of [pyrithmic](https://github.com/jacksonwoody/pyrithmic), but the code has been completely rewritten.

## Key Enhancements

This repo introduces several key improvements and new features over the original repository, ensuring compatibility with modern Python environments and providing additional functionality:

- **Python 3.11+ Compatibility**: Fully tested and supported on the latest Python versions.
- **Robust architecture**: Engineered for concurrency with built-in automatic reconnection logic. Ideal for long-running, fault-tolerant applications.
- **Multi-account support**: select which account to operate on, removing the limitation of a fixed primary account.
- **STOP Orders support**: includes the ability to place and manage STOP orders.
- **Best Bid Offer (BBO) Streaming**: Integrates real-time Best Bid Offer tick streaming. 
- **Historical + Streaming Time Bars**: Access both historical time bars and real-time bar streaming for time-based strategies.

The most significant architectural shift is the adoption of an async-first design, delivering improved responsiveness, efficient I/O handling, and better scalability for real-time trading and market data ingestion.


## Installation

```
pip install async_rithmic
```

> ⚠ **Test Environment Limitation**:
The test environment does not include historical market data.

## Documentation

[See the official documentation for usage examples](https://async-rithmic.readthedocs.io/en/latest/)

## Testing

To execute the tests, use the following command: `make tests`

## License

This project is licensed under the MIT License.
See [LICENSE](LICENSE) for details.
