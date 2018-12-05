# ipset-http
Simple HTTP API to add ipset entries with timeout

Run:

```bash
sudo python3 ipset_http.py --port 9000 --set-name blocked --timeout 60 --whitelist 127.0.0.0/8,172.16.30.0/24
```

Use HTTP API to modity ipsets:

```bash
# Add IP to default set with default timeout
curl "http://127.0.0.1:9000/?add_ip=192.168.0.1"
# Add IP to given set with given timeout
curl "http://127.0.0.1:9000/?add_ip=192.168.0.2&set_name=blocked2&timeout=180"
```
