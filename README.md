# Python Rithmic API

[![PyPI - Version](https://img.shields.io/pypi/v/async_rithmic)](https://pypi.org/project/async-rithmic/)
[![CI](https://github.com/rundef/async_rithmic/actions/workflows/ci.yml/badge.svg)](https://github.com/rundef/async_rithmic/actions/workflows/ci.yml)
[![Documentation](https://app.readthedocs.org/projects/async-rithmic/badge/?version=latest)](https://async-rithmic.readthedocs.io/en/latest/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/async_rithmic)](https://pypistats.org/packages/async-rithmic)

`async_rithmic` is a modern, high-performance Python API for the Rithmic trading platform.
Built with an async-first architecture, it enables robust, scalable access to Rithmic's Protocol Buffer interface for both live trading and real-time market data.

Designed with reliability and extensibility in mind, `async_rithmic` is a strong foundation for advanced trading systems requiring:

- Low-latency connectivity
- Real-time streaming capabilities
- Fault-tolerant, long-running operation
- Full control over order management and data handling

## ✨ Key Features

- ✅ **Python 3.10+ Compatibility**: Fully tested and supported.
- 🛠️ **Robust architecture**: Built-in reconnection & fault-tolerance.
    - [**Automatic reconnection**](https://async-rithmic.readthedocs.io/en/latest/connection.html#custom-reconnection-settings): Resilient to network interruptions with customizable backoff and retry logic.
    - [**Automatic retries**](https://async-rithmic.readthedocs.io/en/latest/connection.html#custom-retry-settings): Configure how many times a slow request will be retried and for how long, making your client more resilient to network delays and backend slowness.
- 👥 **Multi-account support**
- 📊 **Historical + Live Time Bars**: Ideal for time-based strategies.
- 🎯 **Live Tick Data & Best Bid/Ask Streaming**: Fine-grained market data for real-time decision-making.
- ⚡ **Async-first design**: Better scalability & responsiveness.

## 📦 Installation

```
pip install async_rithmic
```

## 📘 Documentation

👉 [See the official documentation for usage examples](https://async-rithmic.readthedocs.io/en/latest/)

## 🧪 Testing

To execute the tests, use the following command: `make tests`

## 📄 License

This project is licensed under the MIT License.
See [LICENSE](LICENSE) for details.
