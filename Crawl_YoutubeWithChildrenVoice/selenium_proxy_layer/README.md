# 🔄 Selenium Proxy Layer for IP Rotation

A comprehensive IP rotation solution for your YouTube crawler using Selenium-managed browser instances. This proxy layer sits between your crawler and the internet, automatically rotating IP addresses to avoid rate limits and blocks.

## 🚀 Features

- **Transparent IP Rotation**: Automatically switches IP addresses without code changes
- **Multiple Rotation Strategies**: Time-based, request-based, failure-based, and hybrid
- **Browser Pool Management**: Manages multiple browser instances with different proxies
- **Health Monitoring**: Automatically detects and recovers from failed browsers
- **Zero-Code Integration**: Works with existing crawler via environment variables
- **Admin Interface**: Built-in monitoring and control endpoints
- **Configurable**: Extensive configuration options via JSON file

## 📁 Architecture

```
YouTube Crawler → Local Proxy Server → Selenium Browser Pool → Different IPs → Internet
```

### Components:

- **`ProxyManager`**: Main orchestrator and entry point
- **`HTTPProxyServer`**: Local HTTP proxy server that intercepts requests
- **`BrowserPool`**: Manages multiple Selenium browser instances
- **`RotationStrategies`**: Determines when to switch IPs
- **`HealthMonitor`**: Monitors browser health and performs recovery
- **`Integration`**: Helper utilities for easy crawler integration

## 🛠️ Installation

1. **Install dependencies**:

```bash
pip install selenium webdriver-manager
```

2. **Install browser drivers** (Chrome is recommended):
   - Chrome: Download ChromeDriver or use webdriver-manager
   - Firefox: Download GeckoDriver
   - Edge: Download EdgeDriver

## ⚙️ Configuration

Edit `proxy_config.json` to customize the proxy layer:

```json
{
  "local_proxy_host": "127.0.0.1",
  "local_proxy_port": 8080,
  "browser_type": "chrome",
  "browser_pool_size": 3,
  "headless": true,
  "proxy_list": [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080"
  ],
  "rotation_strategy": "request_based",
  "rotation_interval": 10
}
```

### Key Settings:

- **`browser_pool_size`**: Number of browser instances (more = better rotation)
- **`proxy_list`**: External proxies to route through (optional)
- **`rotation_strategy`**: When to rotate IPs
  - `time_based`: Rotate every N seconds
  - `request_based`: Rotate every N requests
  - `failure_based`: Rotate on failures
  - `hybrid`: Combines all strategies
- **`rotation_interval`**: Frequency of rotation

## 🏃‍♂️ Usage

### Option 1: Simple Launcher

```bash
python selenium_proxy_layer/launcher.py
```

### Option 2: Integration with Crawler

```python
from selenium_proxy_layer.integration import enable_proxy_for_crawler

# Automatically start proxy and configure environment
with enable_proxy_for_crawler() as proxy:
    # Run your crawler - it will automatically use rotating IPs
    from youtube_video_crawler import main
    main()
```

### Option 3: Environment Variables

```bash
# Start proxy layer
python selenium_proxy_layer/launcher.py &

# Set environment variables
export HTTP_PROXY=http://127.0.0.1:8080
export HTTPS_PROXY=http://127.0.0.1:8080

# Run your crawler
python youtube_video_crawler.py
```

### Option 4: Programmatic Control

```python
from selenium_proxy_layer import SeleniumProxyManager

# Create and start proxy manager
manager = SeleniumProxyManager()
manager.start()

# Your crawler will now automatically use rotating IPs
# via environment variables set by the proxy manager

# Stop when done
manager.stop()
```

## 📊 Monitoring

### Admin Endpoints

While the proxy is running, you can monitor it via HTTP:

```bash
# Get status
curl http://127.0.0.1:8080/_proxy_admin/status

# Get health report
curl http://127.0.0.1:8080/_proxy_admin/health

# Force rotation
curl http://127.0.0.1:8080/_proxy_admin/force_rotation
```

### Status Information

The status endpoint returns comprehensive information:

- **Server Status**: Uptime, request counts, success rates
- **Browser Pool**: Health of each browser instance
- **Rotation Strategy**: Current rotation statistics
- **Performance Metrics**: Response times, error rates

## 🔧 Advanced Configuration

### External Proxies

Add external proxies to `proxy_list` for additional IP rotation:

```json
{
  "proxy_list": [
    "http://username:password@proxy1.com:8080",
    "socks5://proxy2.com:1080",
    "http://proxy3.com:3128"
  ]
}
```

### Browser Options

Customize browser behavior:

```json
{
  "browser_type": "chrome",
  "headless": true,
  "browser_timeout": 30,
  "page_load_timeout": 20
}
```

### Rotation Strategies

Fine-tune rotation behavior:

```json
{
  "rotation_strategy": "hybrid",
  "rotation_interval": 15,
  "health_check_interval": 60
}
```

## 🔍 Troubleshooting

### Common Issues

1. **"No healthy browsers available"**

   - Check browser driver installation
   - Verify proxy list (if using external proxies)
   - Check browser compatibility

2. **Slow startup**

   - Reduce `browser_pool_size`
   - Use `headless: true`
   - Check network connectivity

3. **High failure rate**
   - Increase `browser_timeout`
   - Check external proxy reliability
   - Monitor health endpoints

### Debug Mode

Enable detailed logging:

```json
{
  "log_level": "DEBUG",
  "log_requests": true,
  "log_responses": true
}
```

### Testing Without External Proxies

The system works without external proxies by rotating between browser instances with different user agents and session states, providing basic IP variation through browser fingerprinting.

## 🏗️ Integration Examples

### With YouTube Crawler

```python
# Run crawler with automatic IP rotation
from selenium_proxy_layer.integration import run_crawler_with_proxy
from youtube_video_crawler import main as crawler_main

run_crawler_with_proxy(crawler_main)
```

### Custom Integration

```python
import os
from selenium_proxy_layer import SeleniumProxyManager

def run_with_proxy():
    manager = SeleniumProxyManager()

    try:
        manager.start()

        # Environment is automatically configured
        # Your existing HTTP requests will now use the proxy

        # Run your application
        your_application_main()

    finally:
        manager.stop()
```

## 📝 Logs

The proxy layer creates detailed logs:

- **`selenium_proxy.log`**: Main log file
- Console output with status updates
- Admin endpoints for real-time monitoring

## 🔒 Security Notes

- The proxy server runs locally and is not exposed to external networks
- External proxy credentials are handled securely
- Browser instances are isolated and cleaned up properly
- No sensitive data is logged by default

## 🚀 Performance Tips

1. **Optimize Browser Pool**: 3-5 browsers usually provide good balance
2. **Use Headless Mode**: Significantly faster browser operations
3. **Configure Timeouts**: Adjust based on your network conditions
4. **Monitor Health**: Use admin endpoints to track performance
5. **External Proxies**: High-quality proxies improve reliability

## 🆘 Support

If you encounter issues:

1. Check the logs in `selenium_proxy.log`
2. Verify browser driver installation
3. Test individual components using admin endpoints
4. Ensure network connectivity to external proxies (if used)

---

**Happy crawling with rotating IPs! 🎯**
