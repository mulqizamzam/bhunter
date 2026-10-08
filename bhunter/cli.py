import click
import yaml
from rich import print

from .scope import Scope
from .recon import enumerate_subdomains
from .scanner import Scanner
from .reporter import render_report, dump_json


def load_cfg(path):
    with open(path) as f:
        return yaml.safe_load(f)


@click.group()
@click.option("--config", default="config.yaml")
@click.pass_context
def main(ctx, config):
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = load_cfg(config)
    ctx.obj["scope"] = Scope(ctx.obj["cfg"])


@main.command()
@click.argument("domain")
@click.pass_context
def recon(ctx, domain):
    cfg = ctx.obj["cfg"]
    found = enumerate_subdomains(domain,
                                 cfg["recon"]["wordlist"],
                                 cfg["recon"]["resolvers"])
    for host, ips in found:
        print(f"[green]{host}[/green] -> {', '.join(ips)}")


@main.command()
@click.argument("urls", nargs=-1)
@click.pass_context
def scan(ctx, urls):
    s = Scanner(ctx.obj["cfg"], ctx.obj["scope"])
    results = [s.probe(u) for u in urls]
    dump_json(results, "scan.json")
    print(render_report(results))


if __name__ == "__main__":
    main()
