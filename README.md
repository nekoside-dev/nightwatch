# Night Watch -- Server Health Checker

# Features

- Report usage of each disk partition
- Check whether specified TCP port(s) are listening
- Check whether specified systemd services are active
- Output results in JSON format

# Usage

- `-h` `--help`
- `-p` `--port`
- `-u` `--unit`
- `-o` `--output` default output.json
- `-v` `-V` `--version`
- `-t` `--threshold` default 85%

# Example

```sh
python3 check.py -p 22,443 -u sshd,nginx -o output.json
```
