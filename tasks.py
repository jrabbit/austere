from pprint import pprint

import attr
from invoke import task

@task
def docker_gauntlet(c):
    "there's so many ways to fuck this up on install let's try them all!"
    proj_name = "austere"
    versions_list = ["3.7", "3.8", "3"]
    for py_version in versions_list:
        c.run(f"docker pull python:{py_version}")
    @attr.s
    class Strat():
        name = attr.ib()
        cmd = attr.ib()
        wheel = attr.ib(default=None)
    whl_version = "0.3.0"
    strats = [Strat(name="pip_wheel", cmd=f"pip install /srv/src/{proj_name}/dist/{{wheel}} && austere version", wheel="austere-{}-py3-none-any.whl".format(whl_version)),
              Strat(name="poetry_1_src", cmd=f"pip install --pre poetry>=1 && cd /srv/src/{proj_name} && poetry install && poetry run austere version"),
              Strat(name="poetry_stable_src", cmd=f"pip install poetry && cd /srv/src/{proj_name} && poetry install && poetry run austere version"),
             ]
    results = {}
    for py_version in versions_list:
        # docker scripting to install via pip, pipenv and setuptools (the first two work normally, but test build arefacts)
        for strat in strats:
            print(py_version, strat.name)
            if strat.wheel:
                lcmd = strat.cmd.format(wheel=strat.wheel)
            else:
                lcmd = strat.cmd
            ret = c.run(f"docker run -v $PWD:/srv/src/{proj_name} -v $PWD/misc/docker_caches:/root/.cache --rm -it python:{py_version} bash -c '{lcmd}'", pty=True, warn=True)
            results[f"{py_version}_{strat.name}"] = ret.ok
    pprint(results)
