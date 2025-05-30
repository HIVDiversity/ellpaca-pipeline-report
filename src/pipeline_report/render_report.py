# from jinja2 import Environment, FileSystemLoader
# from datetime import datetime
# import os
# from pathlib import Path


# def hydrate_template(data: dict, template: Path):
#     # Set up the environment (assuming your template is in the "templates" folder)
#     env = Environment(loader=FileSystemLoader(template))
#     template = env.get_template("template.html")

#     data["report_date"] = datetime.now().strftime("%Y-%m-%d")

#     # Render the template with data
#     output = template.render(**data)

#     return output


# def render(data: dict, output: Path, template: Path):
#     hydrated_template = hydrate_template(data, template)

#     with output.open(mode="w", encoding="utf") as output_fh:
#         output_fh.write(hydrated_template)
