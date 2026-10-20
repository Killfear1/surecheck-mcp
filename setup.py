from setuptools import setup
setup(name='surecheck-mcp', version='0.2.0', py_modules=['surecheck_mcp'],
      description='Local stdio MCP server for Killfear One: phone check, email check and a small-business lead agent',
      python_requires='>=3.8', entry_points={'console_scripts':['surecheck-mcp=surecheck_mcp:main']})
