# mullvad-checker

a fast, multithreaded tool to check the validity and expiry of mullvad account codes using proxy rotation.

```
                [ > ] [ checking 1234567890123456 ]
                [ + ] [ 1234567890123456 — 2026-12-31T23:59:59+00:00 ] [ 0.84s ]
                [ X ] [ 9876543210987654 ]
```

---

## features

- multithreaded — each proxy runs in its own thread
- 7 second cooldown per proxy between checks (rate limit safe)
- supports authenticated proxies in two formats
- saves valid codes with expiry date to `valid_codes.txt`
- colored output via colorama

---

## usage

add your codes to `codes.txt` (one per line):

add your proxies to `proxies.txt` (one per line):
```
login:password@hostname:port
hostname:port@login:password
```

> `proxies.txt` is optional — if empty or missing, runs on direct connection.

valid codes are saved to `valid_codes.txt`:
```
1234567890123456 - 2026-12-31T23:59:59+00:00
```

---

## how it works

```
codes.txt ──► queue
                │
        ┌───────┴───────┐
     proxy 1         proxy 2       (one thread per proxy)
        │               │
     check           check
     wait 7s         wait 7s
        │               │
     check           check
        └───────┬───────┘
                │
          valid_codes.txt
```

each proxy picks a code from the shared queue, checks it against the [mullvad api](https://api.mullvad.net/public/accounts/v1/), waits 7 seconds, then picks the next one. all proxies work in parallel.

---

## files

| file | description |
|---|---|
| `mullvad.py` | main script |
| `codes.txt` | input — account codes to check |
| `proxies.txt` | input — proxy list |
| `valid_codes.txt` | output — valid codes with expiry |
