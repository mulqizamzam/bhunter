# bhunter

## Overview

bhunter is a Python command-line tool for bug-bounty reconnaissance and HTTP probing. It resolves subdomains from a wordlist, sends GET requests only to hosts that pass a scope list, and writes the results to `scan.json` plus a Markdown report rendered from `templates/report.md.j2`.

It is for security researchers doing reconnaissance against targets they are authorized to test. The main use case is: check a program's scope rules in `config.yaml`, enumerate subdomains, then probe individual URLs and keep a machine-readable record.

Features, each traced to the file that implements it:

| Feature | Implemented in | Reachable from the CLI |
|---|---|---|
| Scope gating (in-scope / out-of-scope hosts) | `bhunter/scope.py` | yes, applied by `scan` |
| Subdomain enumeration over DNS | `bhunter/recon.py` | yes, `recon` command |
| HTTP probing with custom headers | `bhunter/scanner.py` | yes, `scan` command |
| JSON + Markdown reporting | `bhunter/reporter.py`, `templates/report.md.j2` | yes, `scan` command |
| Payload injection fuzzer | `bhunter/fuzzer.py`, `rules/*.yaml` | no CLI command calls it |
| Request rate limiter | `bhunter/utils.py` (`RateLimiter`) | no, nothing instantiates it |

The last two rows matter: `bhunter/fuzzer.py` and `bhunter/utils.py` exist in the package but are never imported by `bhunter/cli.py`. The tool is not rate-limited at runtime, and there is no `fuzz` command. See FAQ.

## Prerequisites

| Requirement | Version / value | How to check | Where it comes from |
|---|---|---|---|
| Python | no version is pinned anywhere in this repo | `python3 --version` | **Perlu dikonfirmasi**: `setup.py` has no `python_requires`, there is no `.python-version`, no `pyproject.toml`, and no CI file. Observed working on Python 3.14.4 in this environment. |
| pip | any that can read `requirements.txt` | `python3 -m pip --version` | `setup.py` reads `requirements.txt` for `install_requires` |
| Network egress | DNS to `1.1.1.1` / `8.8.8.8` and HTTP to your targets | `scan` and `recon` both perform live queries | `config.yaml` (`recon.resolvers`, `scan.*`) |
| Wordlist file for `recon` | path set in `config.yaml` under `recon.wordlist` | `ls <path>` | `config.yaml` points at `/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt`, which does not exist on this machine |
| Account, API key, paid service | none | not applicable | no credentials appear in any file in the repo |
| Operating system | no OS constraint is declared | not applicable | **Perlu dikonfirmasi**. Observed running on Linux. |
| pytest | not declared in the repo | `python3 -m pytest --version` | `requirements.txt` does not list it; the test suite needs it |

## Installation

The repository is `https://github.com/mulqizamzam/bhunter`, default branch `main`, license MIT (`LICENSE`).

```bash
git clone https://github.com/mulqizamzam/bhunter.git
cd bhunter
python3 -m pip install -e .
```

`-e` installs the package in editable mode, which is what makes the `bhunter` console script point at this checkout (entry point `bhunter=bhunter.cli:main`, declared in `setup.py`).

First command that proves the install worked:

```bash
bhunter --help
```

Expected shape of the output (observed in this environment, run through an editable install placed under a workspace prefix):

```
Usage: bhunter [OPTIONS] COMMANDS...

Commands:
  recon
  scan
```

If you do not want to touch your interpreter's site-packages, install the dependencies into a directory you own and run the module directly:

```bash
python3 -m pip install --target ./.pylibs -r requirements.txt
PYTHONPATH=./.pylibs python3 -m bhunter.cli --help
```

Both of those were run in this environment: the dependency install exited 0 and the `--help` output matched the block above.

Environment setup: there is no `.env` file, no environment variable, and no setup script in this repo. The only setup step is installing the package. The CLI reads `config.yaml` from the current directory by default.

## Configuration

All configuration lives in `config.yaml`. No environment variable appears anywhere in the code (`os.environ` never occurs), so this table is the complete list of keys.

| Key | Meaning | Value shipped in `config.yaml` | Default if removed |
|---|---|---|---|
| `scope.in_scope` | host patterns that receive traffic, matched with `fnmatch` | `["*.example.com"]` | none, `Scope.__init__` indexes it directly (`cfg["scope"]["in_scope"]`) |
| `scope.out_of_scope` | host patterns denied before the in-scope check | `["admin.example.com"]` | `[]` |
| `scope.max_rps` | intended requests-per-second cap | `10` | `10`, but nothing reads it, see FAQ |
| `recon.wordlist` | file with one subdomain label per line | `/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt` | none, indexed directly |
| `recon.resolvers` | DNS nameservers used by `recon` | `["1.1.1.1", "8.8.8.8"]` | none, indexed directly |
| `scan.timeout` | httpx timeout in seconds | `10` | none, indexed directly |
| `scan.user_agent` | `User-Agent` header | `"bhunter/0.1"` | none, indexed directly |
| `scan.follow_redirects` | whether httpx follows redirects | `false` | none, indexed directly |
| `scan.headers` | extra headers merged over the defaults | `X-Bug-Bounty: "researcher-handle"` | `{}` |
| `fuzz.payload_dir` | rule directory for the fuzzer | `"rules/"` | none, but only `Fuzzer` reads `fuzz` keys, and nothing constructs a `Fuzzer` |
| `fuzz.concurrency` | `ThreadPoolExecutor` worker count | `5` | same as above |

The values above are placeholders. Replace `*.example.com`, `admin.example.com`, and `researcher-handle` with your own targets and handle before running anything.

Scope matching, observed directly by calling `Scope.allows` with the shipped config:

| URL | Allowed |
|---|---|
| `https://example.com/` | no, the pattern `*.example.com` does not match the bare apex |
| `https://www.example.com/` | yes |
| `https://api.example.com/endpoint?q=1` | yes |
| `https://admin.example.com/x` | no, listed in `out_of_scope` |
| `https://other.com/x` | no |

## Database / External Services

No section applies. This project has no database, no migration, and no seed data. The only external contacts are DNS queries to the resolvers in `config.yaml` and HTTP requests to the URLs you pass to `scan`.

## Running the Project

Both commands are subcommands of the `bhunter` group and both accept a `--config` path. The default is `config.yaml`, resolved relative to your current directory.

```bash
bhunter --config config.yaml recon example.com
bhunter --config config.yaml scan https://api.example.com/endpoint?q=1
```

A successful start looks like the `--help` output above. A successful `scan` prints a rendered Markdown report to stdout and writes `scan.json` to the current directory:

```bash
bhunter --config config.yaml scan https://www.example.com/
```

Observed output in this environment:

```
# Bug Hunter Report

## https://www.example.com/
- Status: 200
- Length: 577
- Server: cloudflare
- Content-Type: text/html; charset=utf-8
```

The status, length, and server values are whatever that host returned at the time of the run, so they will differ for you.

There is no server, no daemon, and no port to open. This is a CLI.

## First Use / Quick Start

One complete path from a fresh checkout to a written report, all commands run from the project root:

```bash
cd bhunter
python3 -m pip install -e .
bhunter --help
bhunter --config config.yaml scan https://www.example.com/
```

What each step proves:

1. `pip install -e .` exits 0 and installs `bhunter` plus the eight packages in `requirements.txt`.
2. `bhunter --help` lists `recon` and `scan`, which means the entry point resolves and imports succeed.
3. `scan` prints the Markdown report shown above and leaves `scan.json` next to you:

```json
[
  {
    "url": "https://www.example.com/",
    "status": 200,
    "length": 577,
    "server": "cloudflare",
    "content_type": "text/html; charset=utf-8"
  }
]
```

That file is the success signal: it is written by `dump_json` in `bhunter/reporter.py` after every `scan` run, overwriting the previous one.

For `recon`, the same path works once `recon.wordlist` points at a file that exists on your machine:

```bash
bhunter --config config.yaml recon example.com
```

Expected shape of the output, from `bhunter/cli.py`: one line per resolved host, `host -> ip, ip`. With the shipped wordlist path this machine fails instead, see Troubleshooting.

## Project Structure

```
.
├── LICENSE                  MIT license
├── .gitignore               bytecode, caches, local installs, `scan.json`
├── setup.py                 packaging: name, version, console script
├── requirements.txt         eight runtime dependencies
├── config.yaml              the only configuration file
├── bhunter/
│   ├── __init__.py          __version__ = "0.1.0"
│   ├── cli.py               click group; commands `recon` and `scan`
│   ├── scope.py             Scope.allows(), the authorization gate
│   ├── recon.py             DNS subdomain enumeration
│   ├── scanner.py           httpx GET probe, scope-checked per URL
│   ├── reporter.py          Jinja2 Markdown render + JSON dump
│   ├── fuzzer.py            payload injection, not wired to the CLI
│   └── utils.py             RateLimiter, not wired to anything
├── rules/                   YAML payload rules: sqli, xss, ssrf
├── templates/report.md.j2   Markdown report template
└── tests/test_scope.py      one test for the scope gate
```

Files a newcomer edits first: `config.yaml` (targets and limits) and `bhunter/scope.py` if the matching rules do not fit your program's scope definition.

## Common Commands

Development:

```bash
bhunter --help
bhunter --config config.yaml recon example.com
bhunter --config config.yaml scan https://api.example.com/endpoint?q=1
```

Install:

```bash
python3 -m pip install -e .
python3 -m pip install -r requirements.txt
```

Testing:

```bash
python3 -m pip install pytest
python3 -m pytest tests/ -q
```

Linting, build, database, deployment: no section applies. This repo has no lint or format configuration, no build step, no database, and no deploy target. See Development Guide and Deployment.

## Testing

Runner: pytest. There is no `pytest.ini`, no `pyproject.toml`, and no `setup.cfg`, so pytest runs with defaults from the project root.

```bash
python3 -m pytest tests/ -q
```

Observed result in this environment:

```
1 passed in 0.01s
```

Failure looks like a normal pytest assertion report. The suite has a single test, `tests/test_scope.py::test_in_scope`, which carries three assertions on `Scope.allows`. Nothing else in the package is under test: `recon`, `scanner`, `fuzzer`, `reporter`, and `cli` have no test files.

pytest is not in `requirements.txt`, so install it yourself first.

## Troubleshooting

Each entry below is an error that was actually produced while exercising this checkout.

| Symptom | Likely cause | Check | Fix |
|---|---|---|---|
| `ModuleNotFoundError: No module named 'dns'` when running `bhunter` or `python3 -m bhunter.cli` | dependencies are not installed, so the import at `bhunter/recon.py:1` fails before any command runs | `python3 -c "import dns"` | `python3 -m pip install -e .` (or `python3 -m pip install -r requirements.txt`) |
| `FileNotFoundError: [Errno 2] No such file or directory: 'config.yaml'` | the default `--config` value is relative and you are not in the project root | `pwd` and `ls config.yaml` | run from the project root, or pass `--config /path/to/config.yaml` |
| `jinja2.exceptions.TemplateNotFound: 'report.md.j2' not found in search path: 'templates'` | `render_report` loads templates from a relative `templates` directory, so another working directory cannot see it | `pwd` | run `scan` from the project root; `scan.json` is still written to your current directory before this error appears |
| `FileNotFoundError: [Errno 2] No such file or directory: '/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt'` | the wordlist path in `config.yaml` does not exist on this machine | `ls /usr/share/seclists/Discovery/DNS/` | point `recon.wordlist` at a wordlist you actually have |
| `recon` prints nothing for a domain you expect to resolve | `NXDOMAIN`, `NoAnswer`, and `Timeout` are all swallowed in `bhunter/recon.py` | run a manual `dig @1.1.1.1 <host> A` | confirm the resolver answers; the tool reports no reason for a miss |
| A report section with empty fields for a URL you passed to `scan` | `Scanner.probe` returns `None` for an out-of-scope host and the template still renders it | compare the host against `scope.in_scope` / `scope.out_of_scope` | expected behavior: no request was sent. Add the host to `in_scope` if it should be scanned |
| `https://example.com/` rejected while `https://www.example.com/` is accepted | the `fnmatch` pattern `*.example.com` does not match the apex domain | the table in the Configuration section | add `example.com` to `scope.in_scope` if the apex is in scope |
| `The virtual environment was not created successfully because ensurepip is not available` | the interpreter on this machine has no venv support installed | `python3 -m ensurepip --version` | install the venv package for your distribution, or skip venv and use `pip install -e .` / `--target` as shown in Installation |

## Development Guide

What the files show:

1. Change code under `bhunter/`.
2. Run the test suite: `python3 -m pytest tests/ -q`.
3. Exercise the CLI by hand from the project root: `bhunter --config config.yaml scan <url>`.

What is absent: there is no `CONTRIBUTING.md`, no branch or commit convention, no linter or formatter configuration, and no CI workflow in this repository. Work lands on the `main` branch of `https://github.com/mulqizamzam/bhunter`. **Perlu dikonfirmasi**: who reviews, since no review convention is recorded in any file.

## Deployment

No deployment path exists in this repo. There is no `Dockerfile`, no `docker-compose.yml`, no `Procfile`, no `vercel.json`, and no `k8s/` directory, and the package ships no production environment variables.

The practical distribution path is the one `setup.py` describes: run `python3 -m pip install -e .` on the machine that will do the recon, keep `config.yaml` where you run the command, and use the `bhunter` entry point. That is also the simplest option for a newcomer, because it is the only one the repository supports.

## Security Notes

- Authorization is enforced in one place: `Scope.allows` in `bhunter/scope.py`, checked before every request in `Scanner.probe` and before every payload in `Fuzzer.run`. Out-of-scope hosts receive no traffic. The shipped scope is a placeholder, so read `config.yaml` before the first run.
- `rules/ssrf.yaml` contains payloads aimed at link-local metadata endpoints, loopback services, and `file://` URLs. Use them only against targets you are authorized to test.
- `.gitignore` covers Python bytecode and caches (`__pycache__/`, `*.pyc`), packaging output (`*.egg-info/`, `dist/`, `build/`), local environments (`.venv/`, `.pylibs/`), tool caches (`.pytest_cache/`, `.pip-cache/`), and the run artifact `scan.json`. Everything in this repository that is tracked is meant to be public.
- No file in the repo contains a secret today: `config.yaml` holds only scope patterns, resolvers, headers, and timeouts. Keep it that way. The header `X-Bug-Bounty: researcher-handle` is a placeholder for your own handle, not a credential.
- `scan` writes `scan.json` into the current directory on every run, overwriting the previous one. That file lists the URLs you probed and can include target metadata, so treat it as sensitive output.
- No dependency pinning: `requirements.txt` uses lower bounds only (`requests>=2.31.0` and so on) and there is no lockfile, so a fresh install resolves whatever is current. **Perlu dikonfirmasi** whether that is acceptable for your environment.

## FAQ

**Is bhunter rate-limited?**
No. `bhunter/utils.py` defines a `RateLimiter` class and `config.yaml` carries `scope.max_rps`, but no file imports `RateLimiter` and `Scope` stores `max_rps` without using it. Requests go as fast as the network allows. The earlier README's "Rate-limited" claim did not match the code.

**Can I fuzz with it?**
Not from the CLI. `bhunter/fuzzer.py` has a `Fuzzer` class and `rules/*.yaml` carries `name`, `param`, and `payloads`, but `bhunter/cli.py` defines only `recon` and `scan`, and `Fuzzer` is never constructed. To use it today you would call it from your own script.

**Why do `requests` and `beautifulsoup4` sit in `requirements.txt`?**
They are declared but never imported. A search over `bhunter/*.py` finds imports of `click`, `yaml`, `rich`, `dns.resolver`, `httpx`, `jinja2`, and `concurrent.futures` only.

**Where does the report go?**
Markdown goes to stdout, JSON goes to `scan.json` in the current directory. Both are produced by the `scan` command.

**Does it store anything?**
No database. The only persistent artifacts are `scan.json` and the console output.

**How do I scan more than one URL in one run?**
`scan` accepts multiple arguments: `bhunter --config config.yaml scan <url1> <url2>`. Every URL is scope-checked individually, and out-of-scope entries become `null` in `scan.json`.

## Final Checklist

- [ ] Read `config.yaml` and replaced the placeholder scope with your targets.
- [ ] Confirmed the wordlist path in `recon.wordlist` exists, or skipped `recon`.
- [ ] Ran `python3 --version` and `python3 -m pip --version`.
- [ ] Installed the package with `python3 -m pip install -e .`.
- [ ] Confirmed the install with `bhunter --help`, seeing `recon` and `scan`.
- [ ] Installed pytest with `python3 -m pip install pytest`.
- [ ] Ran `python3 -m pytest tests/ -q` and saw `1 passed`.
- [ ] Ran `bhunter --config config.yaml scan <in-scope-url>` from the project root.
- [ ] Read the Markdown report on stdout and opened `scan.json`.
- [ ] Verified an out-of-scope URL produces no request.
