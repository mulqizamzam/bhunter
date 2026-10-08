from jinja2 import Environment, FileSystemLoader
import json


def render_report(findings, template_dir="templates"):
    env = Environment(loader=FileSystemLoader(template_dir))
    tmpl = env.get_template("report.md.j2")
    return tmpl.render(findings=findings)


def dump_json(findings, path):
    with open(path, "w") as f:
        json.dump(findings, f, indent=2)
