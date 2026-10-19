"""Load pages in a Firefox build that has the dom.indexedDB.mozGetAll.enabled pref.

Usage: harness.py FIREFOX_BINARY MODE PAGES_JSONL OUT_JSONL [WORKERS] [--screenshots]

MODE is "on" (pref true, main-thread lookups of the three members logged) or "off"
(pref false: members not exposed, in windows or workers). Each page gets a fresh tab, which
is closed afterwards so the document reports its use counters
(dom.use_counters.dump.document) to stderr. Results are appended one JSON line per page;
pages already in OUT_JSONL are skipped, so the run can resume.
"""
import concurrent.futures, hashlib, json, os, queue, re, signal, sys, threading, time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

binary, mode, pages_path, out_path = sys.argv[1:5]
workers = int(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5].isdigit() else 4
screenshots = '--screenshots' in sys.argv
assert mode in ('on', 'off')
PAGE_TIMEOUT = 120
SETTLE = 6
shot_dir = os.path.join(os.path.dirname(out_path), 'screenshots', os.path.splitext(os.path.basename(out_path))[0])

LOOKUP_LOGGER = r'''() => {
  const log = console.debug.bind(console);
  for (const [iface, name] of [['IDBObjectStore', 'mozGetAll'], ['IDBIndex', 'mozGetAll'], ['IDBIndex', 'mozGetAllKeys']]) {
    const proto = globalThis[iface] && globalThis[iface].prototype;
    if (!proto) continue;
    const desc = Object.getOwnPropertyDescriptor(proto, name);
    if (!desc) continue;
    let value = desc.value;
    Object.defineProperty(proto, name, {
      configurable: true, enumerable: desc.enumerable,
      get() {
        const frame = (new Error().stack || '').split('\n')[1] || '';
        log('MOZGETALL_LOOKUP ' + iface + '.' + name + ' ' + frame);
        return value;
      },
      set(v) { value = v; },
    });
  }
}'''


def done_pages():
    if not os.path.exists(out_path):
        return set()
    return {json.loads(l)['page'] for l in open(out_path) if l.strip()}


write_lock = threading.Lock()


def write(rec):
    with write_lock, open(out_path, 'a') as f:
        f.write(json.dumps(rec) + '\n')


class Browser:
    def __init__(self, idx):
        self.idx = idx
        self.log_path = os.path.join(os.path.dirname(out_path), f'logs/{mode}-{os.getpid()}-{idx}.log')
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self.start()

    def start(self):
        o = Options()
        o.binary_location = binary
        o.add_argument('-headless')
        o.enable_bidi = True
        for k, v in {
            'dom.indexedDB.mozGetAll.enabled': mode == 'on',
            'dom.use_counters.dump.document': True,
            'dom.use_counters.dump.page': True,
            'dom.use_counters.dump.worker': True,
            'browser.sessionhistory.max_total_viewers': 0,
            'app.update.enabled': False,
            'datareporting.policy.dataSubmissionEnabled': False,
            'browser.shell.checkDefaultBrowser': False,
            'media.autoplay.default': 5,
        }.items():
            o.set_preference(k, v)
        self.log = open(self.log_path, 'ab')
        svc = Service(log_output=self.log, popen_kw={'start_new_session': True})
        self.driver = webdriver.Firefox(options=o, service=svc)
        self.driver.set_window_size(1376, 768)
        self.driver.set_page_load_timeout(60)
        self.home = self.driver.current_window_handle
        self.errors, self.console = [], []
        self.driver.script.add_javascript_error_handler(lambda e: self.errors.append(getattr(e, 'text', str(e))))
        self.driver.script.add_console_message_handler(lambda e: self.console.append(getattr(e, 'text', str(e))))
        if mode == 'on':
            self.driver.script.pin(LOOKUP_LOGGER)

    def kill(self):
        try:
            os.killpg(self.driver.service.process.pid, signal.SIGKILL)
        except Exception:
            pass
        try:
            self.log.close()
        except Exception:
            pass

    def visit(self, page):
        d = self.driver
        self.log.flush()
        offset = os.path.getsize(self.log_path)
        self.errors.clear(); self.console.clear()
        rec = {'page': page['page'], 'rank': page['rank'], 'kind': page['kind'], 'mode': mode, 'ts': time.time()}
        d.switch_to.new_window('tab')
        try:
            d.get(page['page'])
        except Exception as e:
            rec['load_error'] = type(e).__name__
        time.sleep(SETTLE)
        try:
            rec.update(d.execute_script('''return {
              url: location.href, title: document.title,
              text_length: document.body ? document.body.innerText.length : null,
              scroll_width: document.documentElement.scrollWidth,
              scroll_height: document.documentElement.scrollHeight,
              elements: document.getElementsByTagName('*').length}'''))
        except Exception as e:
            rec['eval_error'] = type(e).__name__
        if screenshots:
            os.makedirs(shot_dir, exist_ok=True)
            name = hashlib.sha1(page['page'].encode()).hexdigest()[:16] + '.png'
            try:
                d.save_screenshot(os.path.join(shot_dir, name))
                rec['screenshot'] = name
            except Exception as e:
                rec['screenshot_error'] = type(e).__name__
        d.close()
        d.switch_to.window(self.home)
        time.sleep(2)
        self.log.flush()
        with open(self.log_path, 'rb') as f:
            f.seek(offset)
            lines = f.read().decode('utf8', 'replace').splitlines()
        rec['use_counters'] = sorted({l.strip() for l in lines if l.startswith('USE_COUNTER_') and 'mozgetall' in l.lower().replace('_', '')})
        rec['lookups'] = sorted({c for c in self.console if 'MOZGETALL_LOOKUP' in c})
        rec['errors'] = self.errors[:50]
        return rec


def worker(idx, q):
    b = Browser(idx)
    while True:
        try:
            page = q.get_nowait()
        except queue.Empty:
            break
        ex = concurrent.futures.ThreadPoolExecutor(1)
        fut = ex.submit(b.visit, page)
        try:
            rec = fut.result(timeout=PAGE_TIMEOUT)
        except Exception as e:
            rec = {'page': page['page'], 'rank': page['rank'], 'kind': page['kind'], 'mode': mode,
                   'error': 'timeout' if isinstance(e, concurrent.futures.TimeoutError) else repr(e)[:300]}
            b.kill()
            ex.shutdown(wait=False, cancel_futures=True)
            b = Browser(idx)
        write(rec)
        print(idx, rec.get('error') or '', rec.get('use_counters'), rec.get('lookups'), page['page'], flush=True)
    try:
        b.driver.quit()
    except Exception:
        b.kill()


pages = [json.loads(l) for l in open(pages_path)]
skip = done_pages()
q = queue.Queue()
for p in pages:
    if p['page'] not in skip:
        q.put(p)
print(q.qsize(), 'pages to do', flush=True)
threads = [threading.Thread(target=worker, args=(i, q)) for i in range(workers)]
for t in threads:
    t.start()
for t in threads:
    t.join()
