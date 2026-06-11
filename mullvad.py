import threading
import time
import queue
import requests
from colorama import Fore, Style

codes = "codes.txt"
proxies = "proxies.txt"
validcodes = "valid_codes.txt"
cooldown = 7
api = "https://api.mullvad.net/public/accounts/v1/{}"
results_lock = threading.Lock()
print_lock = threading.Lock()
valid_codes = []
gray = Fore.LIGHTBLACK_EX
orange = Fore.LIGHTYELLOW_EX
lightblue = Fore.LIGHTBLUE_EX

class log:
    @staticmethod
    def slog(type, color, message, time):
        msg = f"{gray}                [ {color}{type}{gray} ] [ {color}{message}{gray} ]"
        msg = msg + f" [ {Fore.CYAN}{time:.2f}s{gray} ]" if time != None else msg
        print(msg)

    @staticmethod
    def ilog(type, color, message):
        msg = f"{gray}                [ {color}{type}{gray} ] [ {color}{message}{gray} ]"
        inputmsg = input(msg + " ")
        return inputmsg

    @staticmethod
    def log(type, color, message):
        msg = f"{gray}                [ {color}{type}{gray} ] [ {color}{message}{gray} ]{Style.RESET_ALL}"
        print(msg)

    @staticmethod
    def success(message, time=None):
        log.slog('+', Fore.GREEN, message, time)

    @staticmethod
    def fail(message):
        log.log("X", Fore.RED, message)

    @staticmethod
    def warn(message, prefix="w"):
        log.log(prefix, Fore.YELLOW, message)

    @staticmethod
    def info(message, prefix="i"):
        log.log(prefix, lightblue, message)

def safe_log(fn, *args, **kwargs):
    with print_lock:
        fn(*args, **kwargs)

def parse_proxy(raw):
    raw = raw.strip()
    if "@" not in raw:
        return None
    a, b = raw.split("@", 1)
    if ":" in a and "." in b:
        login_pass, host_port = a, b
    else:
        host_port, login_pass = a, b
    return f"http://{login_pass}@{host_port}"

def check_code(code, proxy_url):
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    try:
        r = requests.get(api.format(code), proxies=proxies, timeout=15)
        if r.status_code == 200:
            data = r.json()
            expiry = data.get("expiry") or data.get("expires") or data.get("paid_until") or "N/A"
            return True, expiry
        if r.status_code == 404:
            return False, None
        safe_log(log.warn, f"{code} → HTTP {r.status_code}")
        return False, None
    except requests.exceptions.ProxyError:
        safe_log(log.warn, f"proxy error: {proxy_url}", "p")
        return False, None
    except requests.exceptions.Timeout:
        safe_log(log.warn, f"timeout: {proxy_url}", "t")
        return False, None
    except Exception as e:
        safe_log(log.fail, f"{code}: {e}")
        return False, None

def worker(proxy_url, code_queue):
    while True:
        try:
            code = code_queue.get_nowait()
        except queue.Empty:
            break

        safe_log(log.info, f"{code}", ">")
        t0 = time.time()
        valid, expiry = check_code(code, proxy_url)

        if valid:
            safe_log(log.success, f"{code} — {expiry}", time.time() - t0)
            with results_lock:
                valid_codes.append((code, expiry))
        else:
            safe_log(log.fail, f"{code}")

        code_queue.task_done()

        if not code_queue.empty():
            time.sleep(cooldown)
def load_lines(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        return []

def main():
    codes = load_lines("codes.txt")
    raw_proxies = load_lines("proxies.txt")

    if not codes:
        log.fail("no codes in codes.txt")

    proxy_urls = []
    for raw in raw_proxies:
        parsed = parse_proxy(raw)
        if parsed:
            proxy_urls.append(parsed)
        else:
            log.warn(f"invalid format: {raw}", "skip")

    log.info(f"codes: {len(codes)}  proxies: {len(proxy_urls)}  cooldown: {cooldown}s")

    code_queue = queue.Queue()
    for code in codes:
        code_queue.put(code)

    pool = proxy_urls if proxy_urls else [None]
    threads = [threading.Thread(target=worker, args=(p, code_queue), daemon=True) for p in pool]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if valid_codes:
        with open(validcodes, "w", encoding="utf-8") as f:
            for code, expiry in valid_codes:
                f.write(f"{code} - {expiry}\n")
        log.success(f"{len(valid_codes)} valid codes saved to {validcodes}")
    else:
        log.fail("no valid codes found")

if __name__ == "__main__":
    main()