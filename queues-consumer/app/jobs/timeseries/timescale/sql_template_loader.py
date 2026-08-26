"""
This module is a singleton for SQL templates.
Because every job that needs to execute some SQL, it 
is better to have a single instance of the template loader,
with the loaded templates, so we don't have to load the
templates every time a job is executed.
"""

import jinja2

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("/code/app/jobs/timeseries/timescale/sql_templates/"),
)

check_schema_template = jinja_env.get_template("check_schema.sql.jinja")
